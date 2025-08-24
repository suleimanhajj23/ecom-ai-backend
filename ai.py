# ai.py
import os, json
import httpx
from dotenv import load_dotenv
load_dotenv()

API_URL = os.getenv("LLM_API_URL")
API_KEY = os.getenv("LLM_API_KEY")
MODEL  = os.getenv("LLM_MODEL", "gpt-4o-mini")

PROMPT = """You are an expert DTC marketer.
From ONLY the product_name below, infer plausible attributes and produce STRICT JSON.

Always return ALL keys:
- SEO_title (<=70 chars)
- description (<=300 chars)
- benefit_bullets (exactly 3 items)
- tiktok_caption (<=150 chars)
- instagram_ad_caption (<=2200 chars)
- email_subjects (exactly 3 items)
- keywords_used (<=10 items)

Focus your effort on these requested channels (may be empty): {include}.
Adopt the requested brand voice: {voice}.

Return valid JSON ONLY, no markdown, no prose.

product_name: "{name}"
"""

async def call_llm(name: str, include=None, voice="default") -> dict:
    if not (API_URL and API_KEY):
        raise RuntimeError("LLM not configured")

    include = include or []
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Return only valid JSON matching the schema."},
            {"role": "user", "content": PROMPT.format(
                name=name.replace('"','\\"'),
                include=", ".join(include),
                voice=voice
            )}
        ],
        "temperature": 0.4
    }

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(API_URL, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    text = (
        data.get("choices",[{}])[0]
            .get("message",{})
            .get("content","").strip()
    )

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{"); end = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
        raise
