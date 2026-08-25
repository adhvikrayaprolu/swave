# Firebase Admin SDK configuration - reads credentials from env vars
import os
import json
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth


def _init_firebase_admin_if_available() -> bool:
    """Initialize Firebase Admin if credentials are available in env."""
    try:
        firebase_admin.get_app()
        return True
    except ValueError:
        pass

    gac_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    creds_json_str = os.environ.get("FIREBASE_CREDENTIALS_JSON")

    try:
        if gac_path and os.path.exists(gac_path):
            cred = credentials.Certificate(gac_path)
            firebase_admin.initialize_app(cred)
            return True
        
        if creds_json_str:
            cred_data = json.loads(creds_json_str)
            cred = credentials.Certificate(cred_data)
            firebase_admin.initialize_app(cred)
            return True
    except (json.JSONDecodeError, ValueError, FileNotFoundError):
        return False

    return False


FIREBASE_ADMIN_READY = _init_firebase_admin_if_available()


def verify_firebase_token(id_token: str):
    """Verify Firebase ID token and return decoded payload, or None if invalid."""
    if not FIREBASE_ADMIN_READY:
        return None
    
    try:
        return firebase_auth.verify_id_token(id_token)
    except ValueError:
        return None
    except Exception:
        return None

