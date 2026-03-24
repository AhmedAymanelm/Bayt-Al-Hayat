from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import date, time

class ProfilePictureUpdateRequest(BaseModel):
    profile_picture_url: str = Field(..., description="رابط صورة الملف الشخصي")

class BirthDetailsUpdateRequest(BaseModel):
    date_of_birth: date = Field(..., description="تاريخ الميلاد")
    place_of_birth: str = Field(..., description="مكان الميلاد")
    time_of_birth: Optional[time] = Field(None, description="وقت الميلاد")

class ProfileResponse(BaseModel):
    id: str
    email: str
    fullname: str
    date_of_birth: date
    place_of_birth: str
    time_of_birth: Optional[time]
    profile_picture_url: Optional[str]

    class Config:
        from_attributes = True
