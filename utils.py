import re
from typing import List, Tuple

PROFANITY = {"damn","shit","fuck"}  # demo-only, keep small
BANNED_CLAIMS = {
    "cures", "guaranteed results", "get rich", "overnight success", "clinically proven"
}
SPAMMY = {"100% free", "no risk", "act now", "limited time only!!!"}

def sanitize(text: str) -> str:
    t = text
    for w in PROFANITY:
        t = re.sub(rf"\b{re.escape(w)}\b", "***", t, flags=re.I)
    for w in BANNED_CLAIMS | SPAMMY:
        t = re.sub(rf"\b{re.escape(w)}\b", "", t, flags=re.I)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t

def apply_voice(text: str, voice: str) -> str:
    if voice == "minimal":
        t = re.sub(r"[^\w\s\.,\-:;']", "", text)
        t = re.sub(r"\s+", " ", t).strip()
        t = re.sub(r"\b(premium|best[- ]seller|ultimate|amazing)\b", "", t, flags=re.I)
        return sanitize(t)
    if voice == "playful":
        t = text
        if not re.search(r"[!🙂🚀✨💥❤️🌟]", t):
            t = "✨ " + t
        return sanitize(t)
    if voice == "luxury":
        t = re.sub(r"[^\w\s\.,\-:;']", "", text)
        t = re.sub(r"\b(cool|awesome|crazy|lit|dope)\b", "refined", t, flags=re.I)
        t = re.sub(r"\b(premium)\b", "exquisite", t, flags=re.I)
        return sanitize(t)
    return sanitize(text)

def infer_category_and_features(name: str) -> Tuple[str, List[str]]:
    n = name.lower()
    category = "general"
    if any(k in n for k in ["backpack", "bag", "tote"]): category = "bags"
    if any(k in n for k in ["serum","cleanser","moisturizer","spf","sunscreen"]): category = "skincare"
    if any(k in n for k in ["headphones","earbuds","charger","adapter","power bank"]): category = "electronics"

    tokens = re.findall(r"[a-z0-9\-\+]+", n)
    stop = {"the","and","with","for","of","by","to"}
    feats = [t for t in tokens if t not in stop and len(t) > 2]
    return category, list(dict.fromkeys(feats))[:8]

def seed_keywords(category: str, feats: List[str]) -> List[str]:
    base_map = {
        "bags": ["lightweight", "waterproof", "laptop", "everyday", "travel"],
        "skincare": ["hydrating", "non-comedogenic", "dermatologist-tested", "fragrance-free"],
        "electronics": ["fast charge", "bluetooth", "noise-cancelling", "battery life"],
        "general": ["premium", "best-seller", "new arrival"]
    }
    base = base_map.get(category, base_map["general"])
    kws = list(dict.fromkeys(base + feats))
    return kws[:10]

def clamp(s: str, max_len: int) -> str:
    return s if len(s) <= max_len else s[:max_len-1].rstrip() + "…"

def baseline_generate(name: str, voice: str = "default"):
    category, feats = infer_category_and_features(name)
    kws = seed_keywords(category, feats)

    seo_title = clamp(f"{name} — {(' '.join(kws[:3])).title()} {category.title()}", 70)
    seo_title = apply_voice(seo_title, voice)

    desc = ("Discover {name}: a {category} designed for {use1}, {use2}, and {use3}. "
            "Built with {feat1} and {feat2} so you get dependable performance every day. "
            "Join thousands who upgraded to {name} for quality without compromise.").format(
        name=name, category=category,
        use1="daily use", use2="travel", use3="efficiency",
        feat1=kws[0] if kws else "quality",
        feat2=kws[1] if len(kws)>1 else "reliability"
    )
    desc = clamp(apply_voice(desc, voice), 300)

    bullets = [
        apply_voice(f"{(kws[0].title() if kws else 'Premium')} performance for everyday reliability", voice),
        apply_voice(f"Designed for {category} needs — practical, durable, and easy to use", voice),
        apply_voice("Backed by quick support and a straightforward return window", voice),
    ]

    tt = clamp(apply_voice(
        f"{name} in action 👀 {(kws[0] if kws else 'refined')} details—see why creators love it! #fyp #{category}",
        voice
    ), 150)

    ig = clamp(apply_voice(
        f"{name}: built for {category} wins. {', '.join(kws[:4])}. Tap to explore.",
        voice
    ), 2200)

    subs = [
        clamp(apply_voice(f"{name}: Limited Drop — Don’t Miss Out", voice), 80),
        clamp(apply_voice(f"{name} Just Landed: See What’s New", voice), 80),
        clamp(apply_voice(f"Why {name} Is Trending This Week", voice), 80),
    ]

    seo_title = sanitize(seo_title)
    desc = sanitize(desc)
    bullets = [sanitize(b) for b in bullets]
    tt = sanitize(tt)
    ig = sanitize(ig)
    subs = [sanitize(s) for s in subs]

    return {
        "SEO_title": seo_title,
        "description": desc,
        "benefit_bullets": bullets,
        "tiktok_caption": tt,
        "instagram_ad_caption": ig,
        "email_subjects": subs,
        "keywords_used": kws
    }
