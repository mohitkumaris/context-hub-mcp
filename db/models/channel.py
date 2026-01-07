import uuid
from sqlalchemy import String, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base
from datetime import datetime


class Channel(Base):
    __tablename__ = "channels"
    __table_args__ = (
        Index("idx_channels_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    youtube_channel_id: Mapped[str] = mapped_column(String, nullable=False)
    channel_name: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=datetime.utcnow)
