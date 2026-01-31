# backend/app/services/schema_matcher.py
from typing import List, Tuple, Dict
import json
import jieba
from difflib import SequenceMatcher
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.core.security import decrypt_data
from app.models.llm_config import LLMConfig
from app.models.neo4j_config import Neo4jConfig


class SchemaMatcher:
    """Schema 匹配器 - 结合 NLP 和 LLM"""

    def __init__(
        self,
        neo4j_session,
        llm_config: dict,
        neo4j_config: dict
    ):
        self.session = neo4j_session
        self.llm = ChatOpenAI(
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
            model=llm_config["model"],
            temperature=0
        )
        self.neo4j_config = neo4j_config
        self._load_synonyms()
        self._load_schema()

    def _load_synonyms(self):
        """加载同义词库"""
        try:
            with open("app/data/synonyms.json", "r", encoding="utf-8") as f:
                self.synonyms = json.load(f)
        except FileNotFoundError:
            self.synonyms = {}

    async def _load_schema(self):
        """从 Neo4j 加载 Schema"""
        # 加载所有类
        result = await self.session.run("MATCH (c:Class:__Schema) RETURN c")
        classes_data = await result.data()
        self.classes = {
            record["c"]["name"]: {
                "uri": record["c"]["uri"],
                "label": record["c"].get("label")
            }
            for record in classes_data
        }

        # 加载所有属性
        result = await self.session.run("MATCH (p:Property:__Schema) RETURN p")
        props_data = await result.data()
        self.properties = {
            record["p"]["name"]: {
                "uri": record["p"]["uri"],
                "label": record["p"].get("label"),
                "type": "ObjectProperty" if "ObjectProperty" in record["p"].get("labels", []) else "DataProperty"
            }
            for record in props_data
        }

    def _tokenize(self, text: str) -> List[str]:
        """中文分词"""
        return list(jieba.cut(text))

    def _fuzzy_match(self, text: str, candidates: Dict, threshold: float = 0.6) -> List[Tuple]:
        """模糊匹配"""
        matches = []
        for name, info in candidates.items():
            # 直接匹配
            if name.lower() in text.lower() or text.lower() in name.lower():
                matches.append((name, 1.0, "exact"))
                continue

            # 同义词匹配
            for syn in self.synonyms.get(name, []):
                if syn.lower() in text.lower():
                    matches.append((name, 0.95, "synonym"))
                    break
            else:
                # 相似度匹配
                ratio = SequenceMatcher(None, name.lower(), text.lower()).ratio()
                if ratio >= threshold:
                    matches.append((name, ratio, "fuzzy"))

        return sorted(matches, key=lambda x: -x[1])

    async def match_entities(self, query: str) -> dict:
        """匹配查询中的实体"""
        tokens = self._tokenize(query)
        entity_matches = {}

        # 对每个分词进行匹配
        for token in tokens:
            if len(token) < 2:  # 跳过太短的词
                continue

            class_matches = self._fuzzy_match(token, self.classes)
            prop_matches = self._fuzzy_match(token, self.properties)

            if class_matches:
                entity_matches[f"class:{token}"] = {
                    "type": "class",
                    "matched": class_matches[0][0],
                    "confidence": class_matches[0][1],
                    "method": class_matches[0][2]
                }
            elif prop_matches:
                entity_matches[f"property:{token}"] = {
                    "type": "property",
                    "matched": prop_matches[0][0],
                    "confidence": prop_matches[0][1],
                    "method": prop_matches[0][2]
                }

        # LLM 增强匹配
        llm_matches = await self._llm_match(query)
        # 合并结果，LLM 结果优先级更高

        return {"entities": entity_matches, "llm_entities": llm_matches}

    async def _llm_match(self, query: str) -> dict:
        """使用 LLM 进行语义匹配"""
        schema_context = self._build_schema_context()

        prompt = ChatPromptTemplate.from_template("""
你是一个知识图谱 Schema 匹配专家。根据用户的查询，识别其中涉及的实体类型和关系。

可用的 Schema 类：
{classes}

可用的关系/属性：
{properties}

用户查询：{query}

请分析查询并返回 JSON 格式：
{{
    "detected_classes": ["类名1", "类名2"],
    "detected_properties": ["属性名1"],
    "detected_entities": ["提到的具体实体名称"],
    "query_type": "path|neighbors|search|statistics",
    "confidence": "high|medium|low"
}}
""")

        chain = prompt | self.llm
        result = await chain.ainvoke({
            "classes": json.dumps(self.classes, ensure_ascii=False, indent=2),
            "properties": json.dumps(self.properties, ensure_ascii=False, indent=2),
            "query": query
        })

        try:
            return json.loads(result.content)
        except:
            return {}

    def _build_schema_context(self) -> str:
        """构建 Schema 上下文描述"""
        lines = ["Classes:"]
        for name, info in self.classes.items():
            label = info.get("label", name)
            lines.append(f"  - {name} ({label})")

        lines.append("\nProperties:")
        for name, info in self.properties.items():
            label = info.get("label", name)
            lines.append(f"  - {name} ({label})")

        return "\n".join(lines)
