from pydantic import BaseModel
from pydantic import EmailStr

class UserCreate(BaseModel):

    email: EmailStr

    password: str

    full_name: str

class UserLogin(BaseModel):

    email: EmailStr

    password: str