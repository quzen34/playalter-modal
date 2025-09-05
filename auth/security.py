from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import secrets
import hashlib
import time
from pydantic import BaseModel
import os

logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Rate limiting configuration
RATE_LIMIT_REQUESTS = 100  # requests per window
RATE_LIMIT_WINDOW = 3600   # 1 hour in seconds

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class User(BaseModel):
    """User model."""
    user_id: str
    username: str
    email: str
    is_active: bool = True
    is_premium: bool = False
    api_key: Optional[str] = None
    rate_limit_tier: str = "basic"  # basic, premium, enterprise

class TokenData(BaseModel):
    """Token data model."""
    user_id: Optional[str] = None
    username: Optional[str] = None
    scopes: list = []

class SecurityManager:
    """Manage authentication and security features."""
    
    def __init__(self):
        self.users_db = {}  # In production, use proper database
        self.rate_limit_store = {}  # In production, use Redis
        self.api_keys = {}  # API key storage
        self.blocked_ips = set()
        self.suspicious_activities = {}
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Get password hash."""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create refresh token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[TokenData]:
        """Verify JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            if payload.get("type") != token_type:
                return None
            
            user_id: str = payload.get("sub")
            username: str = payload.get("username")
            scopes: list = payload.get("scopes", [])
            
            if user_id is None:
                return None
            
            token_data = TokenData(user_id=user_id, username=username, scopes=scopes)
            return token_data
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {str(e)}")
            return None
    
    def generate_api_key(self, user_id: str) -> str:
        """Generate API key for user."""
        api_key = f"pk_{secrets.token_urlsafe(32)}"
        self.api_keys[api_key] = {
            'user_id': user_id,
            'created_at': datetime.utcnow(),
            'last_used': None,
            'usage_count': 0
        }
        return api_key
    
    def verify_api_key(self, api_key: str) -> Optional[str]:
        """Verify API key and return user_id."""
        if api_key in self.api_keys:
            key_data = self.api_keys[api_key]
            key_data['last_used'] = datetime.utcnow()
            key_data['usage_count'] += 1
            return key_data['user_id']
        return None
    
    def create_user(self, username: str, email: str, password: str) -> User:
        """Create new user."""
        user_id = secrets.token_urlsafe(16)
        hashed_password = self.get_password_hash(password)
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            is_active=True,
            is_premium=False,
            rate_limit_tier="basic"
        )
        
        # Store user (in production, use proper database)
        self.users_db[user_id] = {
            'user': user,
            'password_hash': hashed_password,
            'created_at': datetime.utcnow(),
            'login_attempts': 0,
            'last_login': None
        }
        
        return user
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username/password."""
        for user_data in self.users_db.values():
            user = user_data['user']
            if user.username == username or user.email == username:
                if self.verify_password(password, user_data['password_hash']):
                    user_data['last_login'] = datetime.utcnow()
                    user_data['login_attempts'] = 0
                    return user
                else:
                    user_data['login_attempts'] += 1
                    if user_data['login_attempts'] > 5:
                        logger.warning(f"Multiple failed login attempts for user: {username}")
                        self._flag_suspicious_activity(user.user_id, "multiple_failed_logins")
        return None
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        user_data = self.users_db.get(user_id)
        return user_data['user'] if user_data else None
    
    def check_rate_limit(self, identifier: str, tier: str = "basic") -> bool:
        """Check rate limiting for user/IP."""
        current_time = int(time.time())
        window_start = current_time - RATE_LIMIT_WINDOW
        
        # Get rate limits based on tier
        limits = {
            "basic": {"requests": 100, "window": 3600},
            "premium": {"requests": 500, "window": 3600},
            "enterprise": {"requests": 2000, "window": 3600}
        }
        
        limit_config = limits.get(tier, limits["basic"])
        
        # Initialize or clean old entries
        if identifier not in self.rate_limit_store:
            self.rate_limit_store[identifier] = []
        
        # Remove old requests outside window
        self.rate_limit_store[identifier] = [
            req_time for req_time in self.rate_limit_store[identifier]
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(self.rate_limit_store[identifier]) < limit_config["requests"]:
            self.rate_limit_store[identifier].append(current_time)
            return True
        
        # Log rate limit violation
        logger.warning(f"Rate limit exceeded for {identifier} (tier: {tier})")
        self._flag_suspicious_activity(identifier, "rate_limit_exceeded")
        return False
    
    def validate_request_content(self, content: bytes, max_size: int = 10 * 1024 * 1024) -> bool:
        """Validate request content for security."""
        # Check file size
        if len(content) > max_size:
            return False
        
        # Check for malicious content patterns
        suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'<?php',
            b'<%',
            b'eval(',
            b'exec('
        ]
        
        content_lower = content.lower()
        for pattern in suspicious_patterns:
            if pattern in content_lower:
                logger.warning(f"Suspicious content pattern detected: {pattern}")
                return False
        
        return True
    
    def _flag_suspicious_activity(self, identifier: str, activity_type: str):
        """Flag suspicious activity."""
        if identifier not in self.suspicious_activities:
            self.suspicious_activities[identifier] = []
        
        self.suspicious_activities[identifier].append({
            'type': activity_type,
            'timestamp': datetime.utcnow(),
            'ip_address': None  # Would be populated with actual IP
        })
        
        # Auto-block after multiple suspicious activities
        if len(self.suspicious_activities[identifier]) >= 5:
            self.blocked_ips.add(identifier)
            logger.error(f"Identifier {identifier} blocked due to suspicious activities")
    
    def is_blocked(self, identifier: str) -> bool:
        """Check if identifier is blocked."""
        return identifier in self.blocked_ips
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize uploaded filename."""
        # Remove path traversal attempts
        filename = os.path.basename(filename)
        
        # Remove dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', '\0']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:250 - len(ext)] + ext
        
        return filename
    
    def generate_secure_hash(self, data: str) -> str:
        """Generate secure hash of data."""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000)
        return f"{salt}:{hash_obj.hex()}"
    
    def verify_secure_hash(self, data: str, stored_hash: str) -> bool:
        """Verify secure hash."""
        try:
            salt, hash_hex = stored_hash.split(':', 1)
            hash_obj = hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000)
            return hash_obj.hex() == hash_hex
        except:
            return False

# Global security manager instance
security_manager = SecurityManager()

# Dependency functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user from token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Try JWT token first
        token_data = security_manager.verify_token(credentials.credentials)
        if token_data and token_data.user_id:
            user = security_manager.get_user(token_data.user_id)
            if user:
                return user
        
        # Try API key
        user_id = security_manager.verify_api_key(credentials.credentials)
        if user_id:
            user = security_manager.get_user(user_id)
            if user:
                return user
        
        raise credentials_exception
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise credentials_exception

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def check_rate_limit_dependency(current_user: User = Depends(get_current_active_user)):
    """Check rate limiting for current user."""
    if not security_manager.check_rate_limit(current_user.user_id, current_user.rate_limit_tier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )

async def premium_user_required(current_user: User = Depends(get_current_active_user)) -> User:
    """Require premium user access."""
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required for this feature"
        )
    return current_user

def create_demo_users():
    """Create demo users for testing."""
    # Basic user
    basic_user = security_manager.create_user(
        username="demo_basic",
        email="basic@example.com",
        password="demo123"
    )
    
    # Premium user  
    premium_user = security_manager.create_user(
        username="demo_premium", 
        email="premium@example.com",
        password="demo123"
    )
    premium_user.is_premium = True
    premium_user.rate_limit_tier = "premium"
    
    # Generate API keys
    basic_api_key = security_manager.generate_api_key(basic_user.user_id)
    premium_api_key = security_manager.generate_api_key(premium_user.user_id)
    
    logger.info(f"Demo users created:")
    logger.info(f"Basic user API key: {basic_api_key}")
    logger.info(f"Premium user API key: {premium_api_key}")
    
    return {
        'basic_user': {'user': basic_user, 'api_key': basic_api_key},
        'premium_user': {'user': premium_user, 'api_key': premium_api_key}
    }