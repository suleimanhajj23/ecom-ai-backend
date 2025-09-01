# utils.py
import os
import openai
from passlib.context import CryptContext

openai.api_key = os.getenv("OPENAI_API_KEY")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def baseline_generate(product_name: str, voice: str = "default"):
    """
    Generate structured marketing copy for a product using OpenAI.
    Returns a dict with SEO title, description, bullets, captions, etc.
    """

    prompt = f"""
    You are an expert e-commerce copywriter.
    Write structured marketing copy for the product: "{product_name}".
    Voice style: {voice}.

    Respond ONLY in valid JSON with the following fields:
    {{
      "SEO_title": "string (max 70 chars)",
      "description": "string (100–200 words)",
      "benefit_bullets": ["exactly 3 short bullet points"],
      "tiktok_caption": "string (max 150 chars)",
      "instagram_ad_caption": "string (up to 2200 chars)",
      "email_subjects": ["exactly 3 short subject lines"],
      "keywords_used": ["list of 5 short keywords"]
    }}
    """

    response = openai.ChatCompletion.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
)

    return response.choices[0].message.parsed
