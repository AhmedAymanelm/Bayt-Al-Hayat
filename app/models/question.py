from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from datetime import datetime
from app.database import Base


class AssessmentQuestion(Base):
    """Database model for assessment questions (psychology, neuroscience, etc.)"""
    __tablename__ = "assessment_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_type = Column(String, nullable=False, index=True)  # "psychology" | "neuroscience"
    order_index = Column(Integer, nullable=False)                 # ترتيب السؤال
    text = Column(Text, nullable=False)                           # نص السؤال
    options = Column(JSON, nullable=False)                        # الاختيارات (list for psychology, list for neuroscience)
    options_text = Column(JSON, nullable=True)                    # نص الاختيارات (dict for neuroscience: {"A": "...", "B": "..."})
    is_active = Column(Boolean, default=True)                     # تفعيل/تعطيل السؤال
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary for API responses"""
        result = {
            "id": self.id,
            "assessment_type": self.assessment_type,
            "order_index": self.order_index,
            "text": self.text,
            "options": self.options,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if self.options_text:
            result["options_text"] = self.options_text
        return result
