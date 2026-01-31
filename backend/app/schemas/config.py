# backend/app/schemas/config.py
from pydantic import BaseModel


class LLMConfigRequest(BaseModel):
    api_key: str
    base_url: str
    model: str


class LLMConfigResponse(BaseModel):
    base_url: str
    model: str
    # 不返回完整的 api_key，只返回是否已配置
    has_api_key: bool


class Neo4jConfigRequest(BaseModel):
    uri: str
    username: str
    password: str
    database: str = "neo4j"


class Neo4jConfigResponse(BaseModel):
    uri: str
    username: str
    database: str
    # 不返回完整的 password
    has_password: bool


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
