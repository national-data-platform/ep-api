from typing import Union

from pydantic import BaseModel, Field


# Models for user authentication
class Token(BaseModel):
    access_token: str = Field(
        ...,
        description=("The access token provided after successful authentication."),
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
    )
    token_type: str = Field(
        ...,
        description="The type of token provided.",
        json_schema_extra={"example": "bearer"},
    )


class TokenData(BaseModel):
    username: Union[str, None] = Field(
        None,
        description="The username associated with the token.",
        json_schema_extra={"example": "user123"},
    )


class UserLoginRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=1,
        description="The username for authentication.",
        json_schema_extra={"example": "john.doe"},
    )
    password: str = Field(
        ...,
        min_length=1,
        description="The password for authentication.",
        json_schema_extra={"example": "s3cret"},
    )
