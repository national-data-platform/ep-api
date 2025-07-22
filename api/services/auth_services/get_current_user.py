# api/services/auth_services/get_current_user.py
import requests
from typing import Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
import logging

from api.config.swagger_settings import swagger_settings

# HTTP Bearer token scheme
security = HTTPBearer()

# Configure logger
logger = logging.getLogger(__name__)

def get_current_user(token_data = Depends(security)) -> Dict[str, Any]:
    """
    Validate user token and return user information.
    
    Parameters
    ----------
    token_data : HTTPAuthorizationCredentials
        Bearer token from Authorization header
        
    Returns
    -------
    Dict[str, Any]
        User information including roles and groups
        
    Raises
    ------
    HTTPException
        401: If token is invalid or auth service is unavailable
    """
    token = token_data.credentials
    
    # Handle test token
    if token == swagger_settings.test_token:
        return {
            "roles": ["admin", "user"],
            "groups": ["test_group", "developers"],
            "sub": "test_user",
            "username": "test_user"
        }
    
    # Validate with external API
    try:
        response = requests.post(
            f"{swagger_settings.auth_api_url}",
            json={"token": token},
            timeout=10
        )

        # Handle different HTTP status codes from auth service
        if response.status_code == 401:
            logger.warning("Token validation failed - invalid token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        elif response.status_code == 403:
            logger.warning("Token validation failed - access forbidden")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token does not have sufficient permissions",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        elif response.status_code == 500:
            logger.error("Auth service returned internal server error")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Authentication service is experiencing internal issues.",
            )
        
        elif response.status_code != 200:
            logger.error(f"Auth service returned unexpected status code: {response.status_code}.")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Authentication service returned unexpected response (HTTP {response.status_code}).",
            )
        
        data = response.json()
        
        if "error" in data:
            raise Exception(f"Token validation failed: {data['error']}")
        
        return data
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth service unavailable: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )