from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
import re

app = FastAPI()

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

@app.post("/register")
async def register(user: UserRegister):
    # Validate email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, user.email):
        raise HTTPException(status_code=422, detail="Invalid email format")
    
    # Validate password length
    if len(user.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    
    # Return user info without password
    return {
        "message": "User registered successfully",
        "user": {
            "username": user.username,
            "email": user.email
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)