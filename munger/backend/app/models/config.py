"""Configuration model - key-value store for system settings."""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Config(Base):
    """System configuration key-value store."""
    __tablename__ = "configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
