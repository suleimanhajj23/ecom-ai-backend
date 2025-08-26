# utils.py

def baseline_generate(product_name: str, voice: str = "default"):
    """
    Baseline (non-AI) generator.
    Later we can plug in OpenAI or another LLM.
    """
    # Simple placeholder outputs
    return {
        "SEO_title": f"{product_name} – Baseline Generated",
        "description": f"{product_name} is a fantastic product designed for everyday use. "
                       f"This is a baseline description (no AI yet). Voice: {voice}.",
        "benefit_bullets": [
            "Benefit 1: Reliable and easy to use",
            "Benefit 2: Designed to meet your needs",
            "Benefit 3: Backed by great support"
        ],
        "tiktok_caption": f"Check out {product_name}! 🚀",
        "instagram_ad_caption": f"🔥 Transform your life with {product_name}!",
        "email_subjects": [
            f"{product_name} is here for you!",
            f"Discover {product_name} today",
            f"Why people love {product_name}"
        ],
        "keywords_used": ["quality", "reliable", "affordable"]
    }
