import os
from typing import Optional
from fastapi import Header, HTTPException
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("RAGSTAR_AI_API_KEY", "")


def verify_api_key(x_api_key: Optional[str] = Header(default=None)):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
