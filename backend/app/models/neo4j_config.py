# backend/app/models/neo4j_config.py
from datetime import datetime
from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Neo4jConfig(Base):
    __tablename__ = "neo4j_configs"
    __table_args__ = (UniqueConstraint("user_id", name="uq_neo4j_config_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    uri_encrypted: Mapped[str] = mapped_column(String(500), nullable=False)
    username_encrypted: Mapped[str] = mapped_column(String(255), nullable=False)
    password_encrypted: Mapped[str] = mapped_column(String(255), nullable=False)
    database: Mapped[str] = mapped_column(String(100), default="neo4j")
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
