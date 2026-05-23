import os
import json
import base64
import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
import firebase_admin
from firebase_admin import credentials, auth
from app.core.config import get_settings

settings = get_settings()

APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"

# Initialize Firebase Admin if not already initialized
try:
    firebase_admin.get_app()
except ValueError:
    try:
        if settings.FIREBASE_CREDENTIALS_BASE64:
            cred_dict = json.loads(base64.b64decode(settings.FIREBASE_CREDENTIALS_BASE64).decode('utf-8'))
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        elif settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
        elif os.path.exists("firebase_credentials.json"):
            cred = credentials.Certificate("firebase_credentials.json")
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()
    except Exception as e:
        print(f"Firebase initialization warning in social_auth: {e}")

# Simple memory cache for public keys
_keys_cache = {
    "apple": None
}

async def get_apple_public_keys():
    if _keys_cache["apple"]:
        return _keys_cache["apple"]
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(APPLE_KEYS_URL)
            if response.status_code == 200:
                keys = response.json().get("keys", [])
                _keys_cache["apple"] = keys
                return keys
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch Apple public keys: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to fetch Apple public keys")

async def verify_google_token(id_token: str) -> dict:
    try:
        # Verify the Firebase ID token using firebase_admin.auth
        payload = await run_in_threadpool(auth.verify_id_token, id_token)
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Firebase ID token verification failed: {str(e)}"
        )

async def verify_apple_token(identity_token: str) -> dict:
    try:
        # 1. Unverified decode to inspect kid
        header = jwt.get_unverified_header(identity_token)
        kid = header.get("kid")
        if not kid:
            raise HTTPException(status_code=400, detail="Invalid Apple token header")
        
        # 2. Get Apple public keys
        keys = await get_apple_public_keys()
        
        # 3. Find matching key
        matching_key = next((k for k in keys if k["kid"] == kid), None)
        if not matching_key:
            # Clear cache and retry once
            _keys_cache["apple"] = None
            keys = await get_apple_public_keys()
            matching_key = next((k for k in keys if k["kid"] == kid), None)
            if not matching_key:
                raise HTTPException(status_code=400, detail="Apple public key not found")
        
        # 4. Verify token
        payload = jwt.decode(
            identity_token,
            matching_key,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
        
        if payload.get("iss") != "https://appleid.apple.com":
            raise HTTPException(status_code=400, detail="Invalid Apple token issuer")
            
        return payload
    except JWTError as e:
        raise HTTPException(status_code=400, detail=f"Apple token verification failed: {str(e)}")
