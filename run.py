from datetime import datetime, timedelta, timezone
from jose import jwt

SECRET_KEY = "change-this-to-a-long-random-secret"
ALGORITHM = "HS256"

def create_access_token(user_id: str, expires_minutes: int = 60):
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)

    payload = {
        "sub": user_id,
        "exp": expire,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# Example
token = create_access_token("user-123")
print(token)