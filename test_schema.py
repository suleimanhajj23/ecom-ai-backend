# test_schema.py
from pydantic import ValidationError
from schemas import GenerateIn, GenerateOut

def ok(label, fn):
    try:
        fn()
        print(f"[PASS] {label}")
    except Exception as e:
        print(f"[FAIL] {label} -> {type(e).__name__}: {e}")

def test_generate_in_valid():
    _ = GenerateIn(product_name="AquaShield Backpack", voice="minimal")

def test_generate_in_invalid_voice():
    # should fail because voice is not in allowed literals
    try:
        _ = GenerateIn(product_name="X", voice="hyper")
    except ValidationError as e:
        print("[PASS] invalid voice caught")
        print(e)
        return
    raise AssertionError("invalid voice not caught")

def valid_out_payload():
    return {
        "SEO_title": "AquaShield Waterproof Leather Backpack — Lightweight Travel",
        "description": "Discover AquaShield: a bag designed for daily use, travel, and efficiency. Built with waterproof materials and durable stitching so you get dependable performance every day.",
        "benefit_bullets": [
            "Lightweight build for everyday reliability",
            "Designed for travel — practical and durable",
            "Quick support and a straightforward return window"
        ],
        "tiktok_caption": "AquaShield in action 👀 waterproof and ready to go. #fyp #bags",
        "instagram_ad_caption": "AquaShield: built for travel wins. Waterproof, lightweight, durable. Tap to explore.",
        "email_subjects": [
            "AquaShield Just Landed",
            "Why AquaShield Is Trending",
            "Limited Drop — Don’t Miss Out"
        ],
        "keywords_used": ["waterproof", "lightweight", "travel", "bags"]
    }

def test_generate_out_valid():
    _ = GenerateOut(**valid_out_payload())

def test_generate_out_bad_bullets_len():
    bad = valid_out_payload()
    bad["benefit_bullets"] = ["Only one bullet"]
    try:
        _ = GenerateOut(**bad)
    except ValidationError as e:
        print("[PASS] bad bullets length caught")
        print(e)
        return
    raise AssertionError("bad bullets length not caught")

def test_generate_out_long_title():
    bad = valid_out_payload()
    bad["SEO_title"] = "X" * 200  # too long
    try:
        _ = GenerateOut(**bad)
    except ValidationError as e:
        print("[PASS] long SEO title caught")
        print(e)
        return
    raise AssertionError("long SEO title not caught")

if __name__ == "__main__":
    ok("GenerateIn valid", test_generate_in_valid)
    ok("GenerateIn invalid voice", test_generate_in_invalid_voice)
    ok("GenerateOut valid", test_generate_out_valid)
    ok("GenerateOut bullets length validator", test_generate_out_bad_bullets_len)
    ok("GenerateOut max length validator", test_generate_out_long_title)
