import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, status
from app.core.config import get_settings

settings = get_settings()

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"

# Simple memory cache for public keys
_keys_cache = {
    "google": None,
    "apple": None
}

async def get_google_public_keys():
    if _keys_cache["google"]:
        return _keys_cache["google"]
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(GOOGLE_CERTS_URL)
            if response.status_code == 200:
                keys = response.json().get("keys", [])
                _keys_cache["google"] = keys
                return keys
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch Google public keys: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to fetch Google public keys")

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
        # 1. Unverified decode to inspect kid
        header = jwt.get_unverified_header(id_token)
        kid = header.get("kid")
        if not kid:
            raise HTTPException(status_code=400, detail="Invalid Google token header")
        
        # 2. Get Google public keys
        keys = await get_google_public_keys()
        
        # 3. Find matching key
        matching_key = next((k for k in keys if k["kid"] == kid), None)
        if not matching_key:
            # Clear cache and retry once
            _keys_cache["google"] = None
            keys = await get_google_public_keys()
            matching_key = next((k for k in keys if k["kid"] == kid), None)
            if not matching_key:
                raise HTTPException(status_code=400, detail="Google public key not found")
        
        # 4. Verify token
        payload = jwt.decode(
            id_token,
            matching_key,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
        
        if payload.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            raise HTTPException(status_code=400, detail="Invalid token issuer")
            
        return payload
    except JWTError as e:
        raise HTTPException(status_code=400, detail=f"Google token verification failed: {str(e)}")

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
