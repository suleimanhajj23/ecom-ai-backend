import os
import stripe
from fastapi import FastAPI, HTTPException, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from schemas import GenerateIn, GenerateOut, UserCreate, UserLogin, UserOut
from crud import create_user, get_user_by_email, authenticate_user, create_generation, get_generations
from auth import create_access_token, decode_access_token
from database import SessionLocal, engine, Base, get_db
from models import User, Generation
from utils import baseline_generate
from datetime import datetime
from auth import create_access_token

# --- Setup ---
Base.metadata.create_all(bind=engine)
origins = [
    "https://ecomaicopy.netlify.app",  # ✅ your Netlify frontend
    "http://localhost:8000",           # optional local testing
]

app = FastAPI(title="Ecom Copy AI", version="0.6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ecomaicopy.netlify.app"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Stripe keys
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# --- Database Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Plan Rules ---
PLAN_RULES = {
    "basic": {
        "max_generates": 20,
        "features": {"seo", "description", "subjects", "bullets"},
    },
    "pro": {
        "max_generates": 75,
        "features": {"seo", "description", "subjects", "bullets", "instagram", "tiktok"},
    },
    "premium": {
        "max_generates": None,  # unlimited
        "features": {"seo", "description", "subjects", "bullets", "instagram", "tiktok", "emails_full"},
    },
}

ALL_CHANNELS = ["seo", "description", "bullets", "tiktok", "instagram", "subjects"]

# --- Auth ---
@app.post("/signup", response_model=UserOut)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_user(db, user.email, user.password)

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = authenticate_user(db, user.email, user.password)
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer"}

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).get(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.get("/me")
def read_me(current_user: User = Depends(get_current_user)):
    # Default voices available to all plans
    voices_basic = ["default"]
    voices_pro = ["default", "luxury", "playful", "minimal", "trendy", "formal", "persuasive"]

    # Decide allowed voices based on plan
    if current_user.plan == "basic":
        allowed_voices = voices_basic
    elif current_user.plan == "pro":
        allowed_voices = voices_pro
    elif current_user.plan == "premium":
        # Premium can use presets + custom
        allowed_voices = voices_pro + ["custom"]
    else:
        allowed_voices = voices_basic  # fallback

    return {
        "id": current_user.id,
        "email": current_user.email,
        "plan": current_user.plan,
        "monthly_generates": current_user.monthly_generates,
        "free_trial_remaining": max(0, 3 - current_user.monthly_generates) if current_user.plan == "basic" else None,
        "allowed_voices": allowed_voices,
    }

# --- Generate Copy ---
@app.post("/generate", response_model=GenerateOut)
async def generate_copy(
    body: GenerateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # --- Free trial logic (no plan yet) ---
    if current_user.plan == "free":
        if current_user.monthly_generates >= 3:
            raise HTTPException(
                status_code=403,
                detail="Free trial limit reached. Please sign up or upgrade to continue."
            )

    # --- Paid plan logic ---
    else:
        rules = PLAN_RULES[current_user.plan]
        if rules["max_generates"] is not None and current_user.monthly_generates >= rules["max_generates"]:
            raise HTTPException(
                status_code=403,
                detail=f"Monthly limit reached for {current_user.plan} plan. Please upgrade to continue."
            )

        # Check feature availability
        include = body.include or ALL_CHANNELS
        for ch in include:
            if ch not in rules["features"]:
                raise HTTPException(
                    status_code=403,
                    detail=f"{ch} not available on {current_user.plan} plan"
                )

    # --- Generate using AI ---
    result = baseline_generate(body.product_name.strip(), voice=body.voice)
    out = GenerateOut(**result)

    # --- Save Generation ---
    create_generation(db, body.product_name, body.voice, include, out.dict())

    # --- Increment counter ---
    current_user.monthly_generates += 1
    db.commit()

    return out

# --- Premium Email Generator ---
@app.post("/generate_email")
def generate_email(
    product_name: str,
    email_type: str = "promo",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rules = PLAN_RULES[current_user.plan]
    if current_user.plan != "premium":
        raise HTTPException(status_code=403, detail="Upgrade to Premium to access email generator")

    if rules["max_generates"] is not None and current_user.monthly_generates >= rules["max_generates"]:
        raise HTTPException(status_code=403, detail="Monthly limit reached. Upgrade your plan.")

    subject = f"[{email_type.title()}] {product_name} just for you!"
    body = f"Hello,\n\nHere’s a {email_type} email for {product_name}.\n\nCheers,\nThe Team"

    current_user.monthly_generates += 1
    db.commit()

    return {"subject": subject, "body": body}

# --- Billing Portal ---
@app.post("/billing-portal")
def create_billing_portal(current_user: User = Depends(get_current_user)):
    try:
        session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url="https://ecomaicopy.netlify.app/"
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Stripe Checkout (simplified example) ---
@app.post("/create-checkout-session")
def create_checkout_session(plan: str, current_user: User = Depends(get_current_user)):
    if plan not in ["basic", "pro", "premium"]:
        raise HTTPException(status_code=400, detail="Invalid plan")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": os.getenv(f"STRIPE_PRICE_{plan.upper()}"),  # store plan price IDs in env
                "quantity": 1,
            }],
            mode="subscription",
            customer_email=current_user.email,
            metadata={"plan": plan},
            success_url="https://ecomaicopy.netlify.app?success=true",
            cancel_url="https://ecomaicopy.netlify.app?canceled=true",
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Stripe Webhook ---
@app.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        email = session.get("customer_email")
        plan = session["metadata"].get("plan", "basic")  # fallback to basic if missing

        user = db.query(User).filter(User.email == email).first()
        if user:
            user.plan = plan
            user.monthly_generates = 0  # ✅ reset counter on successful upgrade
            db.commit()
            print(f"✅ Upgraded {email} to {plan} and reset monthly_generates")

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        email = subscription.get("customer_email")
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.plan = "basic"
            user.monthly_generates = 0  # reset when downgraded too
            db.commit()
            print(f"❌ Downgraded {email} to basic (subscription cancelled)")

    return {"status": "success"}

# --- Entry Point for Local & Render ---
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))  # Render provides PORT
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)

app.post("/reset")
def reset_users(
    x_api_key: str = Header(...),
    db: Session = Depends(get_db)
):
    secret = os.getenv("RESET_SECRET")
    if x_api_key != secret:
        raise HTTPException(status_code=401, detail="Unauthorized")

    users = db.query(User).all()
    for user in users:
        user.monthly_generates = 0
        user.last_reset = datetime.utcnow()
    db.commit()
    return {"status": "✅ All users reset for the month"}