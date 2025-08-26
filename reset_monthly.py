from datetime import datetime
from database import SessionLocal
from models import User

def reset_all_users():
    db = SessionLocal()
    users = db.query(User).all()
    for user in users:
        user.monthly_generates = 0
        user.last_reset = datetime.utcnow()
    db.commit()
    db.close()
    print("✅ All users reset for the month.")

if __name__ == "__main__":
    reset_all_users()
