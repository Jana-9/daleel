from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict] | None = None


class ErrorResponse(BaseModel):
    """Documents the shared error shape in the OpenAPI schema."""

    error: ErrorDetail


class HealthOut(BaseModel):
    status: str
    database: str
