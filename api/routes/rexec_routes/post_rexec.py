"""
Register route for provisioning user Rexec environments.
"""

from fastapi import APIRouter, HTTPException, Depends, Form
from typing import Annotated, Optional, Dict

from api.services import rexec_services
# from api.services.keycloak_services.get_current_user import get_current_user

router = APIRouter()


@router.post("/rexec", status_code=200)
def create_rexec_server(
    requirments: Annotated[list[str],
        Form(
            title="Requirements",
            description="User-specified package list provided by requirements.txt",
        )
    ],
    user_id: Annotated[str,
        Form(
            title="User ID",
            description="Keycloak (currently idp-test) user id"
        )
    ],
):
    """
    Create a new dspaces instance for a user in a unique namespace.
    """
    group_id = "test-group"
    # user_id = 'test-user'
    try:
        msg = rexec_services.create_rexec_server_resources(group_id, user_id, requirments)
        return {"message": msg}
    except Exception as e:
        print(type(e), e)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
