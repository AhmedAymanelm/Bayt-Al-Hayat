import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class VideoCache(Base):
    """
    Caches generated Runway videos keyed by (zodiac_sign, neuro_pattern).
    Max 60 unique combinations = 60 videos ever generated, then reused forever.
    """
    __tablename__ = "video_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Cache key components
    zodiac_sign = Column(String(50), nullable=False, index=True)
    neuro_pattern = Column(String(50), nullable=False, index=True)

    # Cloudinary video URL (permanent)
    video_url = Column(String, nullable=False)

    # Symbol used for this combo
    symbol_key = Column(String(50), nullable=True)

    # Usage counter - how many users got this video
    hit_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<VideoCache {self.zodiac_sign}+{self.neuro_pattern} hits={self.hit_count}>"
