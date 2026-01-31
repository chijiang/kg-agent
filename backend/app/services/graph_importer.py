# backend/app/services/graph_importer.py
from typing import List
from neo4j import AsyncSession
from app.services.owl_parser import OWLParser, Triple


class GraphImporter:
    """将 OWL 解析结果导入 Neo4j"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def import_schema(self, parser: OWLParser) -> dict:
        """导入 Schema 层"""
        classes = parser.extract_classes()
        properties = parser.extract_properties()

        stats = {"classes": 0, "properties": 0}

        # 导入类
        for cls in classes:
            await self.session.run(
                """
                MERGE (c:Class:__Schema {uri: $uri})
                SET c.name = $name, c.label = $label
                """,
                uri=cls["uri"],
                name=cls["name"],
                label=cls.get("label")
            )
            stats["classes"] += 1

        # 导入属性
        for prop in properties:
            label_prefix = "Object" if prop["type"] == "object" else "Data"
            await self.session.run(
                f"""
                MERGE (p:{label_prefix}Property:__Schema {{uri: $uri}})
                SET p.name = $name, p.label = $label, p.domain = $domain, p.range = $range
                """,
                uri=prop["uri"],
                name=prop["name"],
                label=prop.get("label"),
                domain=prop.get("domain"),
                range=prop.get("range")
            )

            # 建立类与属性的关系
            if prop.get("domain"):
                await self.session.run(
                    """
                    MATCH (c:Class:__Schema {uri: $domain})
                    MATCH (p:Property:__Schema {uri: $uri})
                    MERGE (c)-[:HAS_PROPERTY]->(p)
                    """,
                    domain=prop["domain"],
                    uri=prop["uri"]
                )
            stats["properties"] += 1

        await self._create_schema_indexes()
        return stats

    async def import_instances(self, schema_triples: List[Triple], instance_triples: List[Triple]) -> dict:
        """导入 Instance 层"""
        stats = {"nodes": 0, "relationships": 0}

        # 首先收集所有类型声明
        type_map = {}  # {instance_uri: class_uri}
        for triple in instance_triples:
            if triple.predicate.endswith("type"):
                type_map[triple.subject] = triple.obj

        # 创建实例节点
        for subject_uri, class_uri in type_map.items():
            class_name = class_uri.split("#")[-1].split("/")[-1]
            node_name = subject_uri.split("#")[-1].split("/")[-1]

            await self.session.run(
                f"""
                MERGE (n:{class_name} {{uri: $uri}})
                SET n.name = $name, n.__type = $class_uri, n.__is_instance = true
                """,
                uri=subject_uri,
                name=node_name,
                class_uri=class_uri
            )
            stats["nodes"] += 1

        # 创建关系
        for triple in instance_triples:
            if triple.predicate.endswith("type"):
                continue  # 跳过类型声明

            # 获取关系名称
            rel_name = triple.predicate.split("#")[-1].split("/")[-1]

            await self.session.run(
                """
                MATCH (s {uri: $subject})
                MATCH (o {uri: $object})
                MERGE (s)-[r:%s]->(o)
                """ % rel_name,
                subject=triple.subject,
                object=triple.obj
            )
            stats["relationships"] += 1

        return stats

    async def _create_schema_indexes(self):
        """创建 Schema 层索引"""
        indexes = [
            "CREATE INDEX schema_class_uri IF NOT EXISTS FOR (c:Class:__Schema) ON (c.uri)",
            "CREATE INDEX schema_class_name IF NOT EXISTS FOR (c:Class:__Schema) ON (c.name)",
            "CREATE INDEX schema_prop_uri IF NOT EXISTS FOR (p:Property:__Schema) ON (p.uri)",
            "CREATE INDEX schema_prop_name IF NOT EXISTS FOR (p:Property:__Schema) ON (p.name)",
        ]

        for idx in indexes:
            await self.session.run(idx)
