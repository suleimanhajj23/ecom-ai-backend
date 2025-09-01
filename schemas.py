from pydantic import BaseModel, EmailStr, constr
from typing import List, Optional, Literal

# ----- User -----
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    plan: str

    class Config:
        from_attributes = True

# ----- Copy Generation -----
class GenerateIn(BaseModel):
    product_name: constr(strip_whitespace=True, min_length=2)
    voice: Optional[str] = "default"  # allow free text for premium users

class GenerateOut(BaseModel):
    SEO_title: str
    description: str
    benefit_bullets: List[str]
    tiktok_caption: str
    instagram_ad_caption: str
    email_subjects: List[str]
    keywords_used: List[str]
