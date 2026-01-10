from pydantic import BaseModel

class StartAuthRequest(BaseModel):
    account: str

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    ok: bool