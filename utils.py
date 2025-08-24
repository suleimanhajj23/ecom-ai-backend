# utils.py
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def baseline_generate(product_name: str, voice: str = "default"):
    """
    Generate marketing copy for a product using OpenAI.
    """
    prompt = f"""
    You are an expert e-commerce copywriter.
    Write the following for the product: "{product_name}".
    Voice style: {voice}.

    1. An SEO-friendly product title (max 70 chars).
    2. A compelling product description (100–200 words).
    3. Exactly 3 bullet-point benefits.
    4. 3 engaging email subject lines.
    5. An Instagram ad caption.
    6. A TikTok caption.
    7. A short list of 5 relevant SEO keywords.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.choices[0].message.content

    # For now just return raw text (later we can parse into JSON/structured output)
    return {
        "SEO_title": f"{product_name} – AI Generated",
        "description": text,
        "benefit_bullets": ["Benefit 1", "Benefit 2", "Benefit 3"],
        "tiktok_caption": "Check out this amazing product! 🚀",
        "instagram_ad_caption": "🔥 Transform your life with this product!",
        "email_subjects": ["Subject 1", "Subject 2", "Subject 3"],
        "keywords_used": ["keyword1", "keyword2", "keyword3"]
    }
