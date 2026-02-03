# backend/app/models/neo4j_config.py
from datetime import datetime
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Neo4jConfig(Base):
    __tablename__ = "neo4j_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uri_encrypted: Mapped[str] = mapped_column(String(500), nullable=False)
    username_encrypted: Mapped[str] = mapped_column(String(255), nullable=False)
    password_encrypted: Mapped[str] = mapped_column(String(255), nullable=False)
    database: Mapped[str] = mapped_column(String(100), default="neo4j")
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
