from sqlalchemy.orm import Session
from models import User, Generation
from auth import hash_password, verify_password
from utils import get_password_hash, verify_password

# ----- Users -----
def create_user(db, email: str, password: str):
    hashed_password = get_password_hash(password)
    new_user = User(
        email=email,
        password_hash=hashed_password,
        plan="free",                 # ✅ Start all new users on free plan
        monthly_generates=0,         # start at 0
        free_trial_remaining=3       # ✅ Give them 3 free trial generates
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

# ----- Generations -----
def create_generation(db: Session, product_name: str, voice: str, include: list, output: dict):
    gen = Generation(
        product_name=product_name,
        voice=voice,
        include=",".join(include),
        output=output
    )
    db.add(gen)
    db.commit()
    db.refresh(gen)
    return gen

def get_generations(db: Session, skip: int = 0, limit: int = 20):
    return db.query(Generation).offset(skip).limit(limit).all()
