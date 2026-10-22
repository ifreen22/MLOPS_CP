from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.db import prisma
from app.api.v1 import router as api_v1_router
from prometheus_client import make_asgi_app
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os

from app.api.v1.controllers import auth_controller, system_controller
from app.core.auth import get_password_hash
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)


async def bootstrap_admin_user():
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    if not email or not password:
        raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD must be configured.")
    if len(password.encode("utf-8")) < 12 or len(password.encode("utf-8")) > 72:
        raise RuntimeError("ADMIN_PASSWORD must be between 12 and 72 UTF-8 bytes.")

    existing_user = await prisma.user.find_unique(where={"email": email})
    if existing_user is not None:
        if existing_user.role != "ADMIN":
            raise RuntimeError(
                "ADMIN_EMAIL already belongs to a non-admin account; "
                "refusing to promote it automatically."
            )
        return

    if await prisma.user.count() > 0:
        logger.warning(
            "Configured bootstrap administrator was not created because users "
            "already exist; use an existing administrator account."
        )
        return

    organization = await prisma.organization.find_first()
    if organization is None:
        organization = await prisma.organization.create(
            data={"name": "AIOps Sentinel Local"}
        )

    await prisma.user.create(
        data={
            "organizationId": organization.id,
            "email": email,
            "passwordHash": get_password_hash(password),
            "role": "ADMIN",
        }
    )
    logger.info("Created the configured initial administrator account.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await prisma.connect()
    await bootstrap_admin_user()
    yield
    await prisma.disconnect()

app = FastAPI(title="AIOps Sentinel API", version="1.0.0", lifespan=lifespan)

class SecurityAndCorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        
        response = await call_next(request)
        
        # Inject Secure HTTP Headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

app.add_middleware(SecurityAndCorrelationMiddleware)

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/internal/metrics", metrics_app)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "An internal server error occurred", "details": str(exc)},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


app.include_router(api_v1_router.api_router, prefix="/api/v1")
app.include_router(auth_controller.router, prefix="/api/v1")
app.include_router(system_controller.router, prefix="/api/v1")

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "ready": True}
