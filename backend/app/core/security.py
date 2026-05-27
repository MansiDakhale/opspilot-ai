import os
from dotenv import load_dotenv
from passlib.context import CryptContext

from jose import jwt

from datetime import datetime, timedelta

load_dotenv()

# Read secrets from environment. Fail fast if not provided.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable not set. Add it to your environment or .env file."
    )

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

def hash_password(password: str):

    return pwd_context.hash(password)

def verify_password(
    plain_password,
    hashed_password
):

    return pwd_context.verify(
        plain_password,
        hashed_password
    )

def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not configured")

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt