# backend/app/models/llm_config.py
from datetime import datetime
from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LLMConfig(Base):
    __tablename__ = "llm_configs"
    __table_args__ = (UniqueConstraint("user_id", name="uq_llm_config_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(String(500), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
