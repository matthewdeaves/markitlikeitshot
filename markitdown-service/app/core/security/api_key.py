from datetime import datetime
import secrets
from typing import Optional
from fastapi import Security, HTTPException, Depends
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from sqlmodel import Session, select
from app.models.auth.api_key import APIKey, Role
from app.core.config import settings
from app.db.session import get_db
from app.utils.audit import audit_log
import logging
from passlib.hash import bcrypt

logger = logging.getLogger(__name__)

# Initialize API key header
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER_NAME, auto_error=False)

def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(settings.API_KEY_LENGTH)

def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return bcrypt.hash(key)

def verify_key_hash(key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash."""
    return bcrypt.verify(key, hashed_key)

def create_api_key(
    db: Session,
    name: str,
    role: Role = Role.USER,
    created_by: Optional[int] = None
) -> APIKey:
    """Create a new API key."""
    existing = db.exec(
        select(APIKey).where(APIKey.name == name)
    ).first()
    
    if existing:
        raise ValueError(f"API key with name '{name}' already exists")

    key = generate_api_key()
    hashed_key = hash_api_key(key)
    
    api_key = APIKey(
        key=hashed_key,  # Store hashed key
        name=name,
        role=role,
        created_by=created_by
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    # Audit logging
    audit_log(
        action="create_api_key",
        user_id=str(created_by),
        details=f"Created API key for {name} with role {role}"
    )
    
    # Return the original key (will only be shown once)
    api_key.key = key
    return api_key

def verify_api_key(db: Session, key: str) -> Optional[APIKey]:
    """Verify an API key and update last used timestamp."""
    api_keys = db.exec(
        select(APIKey).where(APIKey.is_active == True)
    ).all()
    
    for api_key in api_keys:
        if verify_key_hash(key, api_key.key):
            api_key.last_used = datetime.utcnow()
            db.commit()
            
            # Audit logging
            audit_log(
                action="api_key_used",
                user_id=str(api_key.id),
                details=f"API key '{api_key.name}' used"
            )
            return api_key
    
    return None

def deactivate_api_key(db: Session, key_id: int, deactivated_by: Optional[int] = None) -> bool:
    """Deactivate an API key."""
    api_key = db.get(APIKey, key_id)
    if api_key:
        api_key.is_active = False
        db.commit()
        
        # Audit logging
        audit_log(
            action="deactivate_api_key",
            user_id=str(deactivated_by),
            details=f"Deactivated API key {api_key.name}"
        )
        return True
    return False

def reactivate_api_key(db: Session, key_id: int, reactivated_by: Optional[int] = None) -> bool:
    """Reactivate an API key."""
    api_key = db.get(APIKey, key_id)
    if api_key:
        api_key.is_active = True
        db.commit()
        
        # Audit logging
        audit_log(
            action="reactivate_api_key",
            user_id=str(reactivated_by),
            details=f"Reactivated API key {api_key.name}"
        )
        return True
    return False

async def get_api_key(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> Optional[APIKey]:
    """
    Dependency for validating API keys in FastAPI endpoints.
    Returns None if API key auth is disabled.
    """
    if not settings.API_KEY_AUTH_ENABLED:
        return None
        
    if not api_key:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="API key required"
        )
    
    key = verify_api_key(db, api_key)
    if not key:
        # Audit logging for failed attempts
        audit_log(
            action="api_key_invalid",
            user_id=None,
            details="Invalid API key attempt",
            status="failure"
        )
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return key

def require_admin(api_key: APIKey = Depends(get_api_key)):
    """
    Dependency for requiring admin role in FastAPI endpoints.
    Must be used after get_api_key dependency.
    """
    if settings.API_KEY_AUTH_ENABLED and (not api_key or api_key.role != Role.ADMIN):
        # Audit logging for unauthorized admin access attempts
        audit_log(
            action="admin_access_denied",
            user_id=str(api_key.id) if api_key else None,
            details="Unauthorized admin access attempt",
            status="failure"
        )
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return api_key

def rotate_api_key(db: Session, key_id: int, rotated_by: Optional[int] = None) -> Optional[APIKey]:
    """
    Rotate (replace) an existing API key while maintaining its settings.
    Returns the updated API key or None if not found.
    """
    api_key = db.get(APIKey, key_id)
    if api_key:
        new_key = generate_api_key()
        api_key.key = hash_api_key(new_key)
        db.commit()
        
        # Audit logging
        audit_log(
            action="rotate_api_key",
            user_id=str(rotated_by),
            details=f"Rotated API key for {api_key.name}"
        )
        
        # Return the new key (will only be shown once)
        api_key.key = new_key
        return api_key
    return None