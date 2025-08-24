import os
import stripe
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from schemas import GenerateIn, GenerateOut, UserCreate, UserLogin, UserOut
from crud import create_user, get_user_by_email, authenticate_user, create_generation, get_generations
from auth import create_access_token, decode_access_token
from database import SessionLocal, engine, Base
from models import User, Generation
from utils import baseline_generate

# --- Setup ---
Base.metadata.create_all(bind=engine)
origins = [
    "https://ecomaicopy.netlify.app",  # ✅ your Netlify frontend
    "http://localhost:8000",           # optional local testing
]

app = FastAPI(title="Ecom Copy AI", version="0.6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ecomaicopy.netlify.app"],   # 👈 not ["*"] if using allow_credentials
    allow_credentials=True,
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

@app.get("/me", response_model=UserOut)
def read_me(current_user: UserOut = Depends(get_current_user)):
    return current_user

# --- Generate Copy ---
@app.post("/generate", response_model=GenerateOut)
async def generate_copy(
    body: GenerateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rules = PLAN_RULES[current_user.plan]

    if rules["max_generates"] is not None and current_user.monthly_generates >= rules["max_generates"]:
        raise HTTPException(status_code=403, detail="Monthly limit reached. Upgrade your plan.")

    include = body.include or ALL_CHANNELS
    for ch in include:
        if ch not in rules["features"]:
            raise HTTPException(status_code=403, detail=f"{ch} not available on {current_user.plan} plan")

    result = baseline_generate(body.product_name.strip(), voice=body.voice)
    out = GenerateOut(**result)

    create_generation(db, body.product_name, body.voice, include, out.dict())
    current_user.monthly_generates += 1
    db.commit()
    return out

@app.get("/history")
def read_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_generations(db)

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

# --- Stripe Checkout (simplified example) ---
@app.post("/create-checkout-session")
def create_checkout_session(plan: str, current_user: User = Depends(get_current_user)):
    if plan not in ["pro", "premium"]:
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
            success_url="https://your-frontend.netlify.app?success=true",
            cancel_url="https://your-frontend.netlify.app?canceled=true",
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
        plan = "pro" if "pro" in session["metadata"]["plan"] else "premium"

        user = db.query(User).filter(User.email == email).first()
        if user:
            user.plan = plan
            db.commit()
            print(f"✅ Upgraded {email} to {plan}")

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        email = subscription.get("customer_email")
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.plan = "basic"
            db.commit()
            print(f"❌ Downgraded {email} to basic (subscription cancelled)")

    return {"status": "success"}
