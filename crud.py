from sqlalchemy.orm import Session
from models import User, Generation
from auth import hash_password, verify_password

# ----- Users -----
def create_user(db: Session, email: str, password: str):
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
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
