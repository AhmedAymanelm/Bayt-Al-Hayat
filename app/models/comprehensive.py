from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ComprehensiveAnswers(BaseModel):
    """Complete answers for all assessments"""
    
    name: str = Field(..., description="User name")
    age: Optional[int] = Field(None, description="User age for letter science")
    
    psychology_answers: List[int] = Field(..., min_length=7, max_length=7)
    
    neuroscience_answers: List[str] = Field(..., min_length=9, max_length=9)
    
    birth_date: str = Field(..., description="YYYY-MM-DD format")
    day_type: str = Field(default="today", description="today/tomorrow/yesterday")
    birth_time: Optional[str] = Field(None, description="HH:MM format")
    birth_place: Optional[str] = Field(None, description="Birth location name")
    gender: Optional[str] = Field(None, description="male/female")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Optional: pre-computed letter result from /letter/analyze
    letter_result: Optional[Dict[str, Any]] = Field(None, description="Pre-computed letter science result")


class ComprehensiveResultsInput(BaseModel):
    """Input model for submitting pre-computed results from individual assessments"""
    
    name: str = Field(..., description="User name")
    
    psychology_result: Dict[str, Any] = Field(
        ..., 
        description="Psychology assessment result containing score, level, message, supportive_messages"
    )
    
    neuroscience_result: Dict[str, Any] = Field(
        ..., 
        description="Neuroscience assessment result containing dominant, secondary, description, scores"
    )
    
    astrology_result: Dict[str, Any] = Field(
        ..., 
        description="Astrology analysis result containing sun_sign, ascendant, psychological_state, etc."
    )
    
    letter_result: Optional[Dict[str, Any]] = Field(
        None,
        description="Letter science result containing governing_letter, guidance_type, guidance (optional)"
    )


class ComprehensiveResult(BaseModel):
    """Complete assessment results"""
    
    psychology: dict
    neuroscience: dict
    astrology: dict
    video: dict
    status: str
    message: str
