import json
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .config import Settings, get_settings
from .schemas import VerificationPayload, VerificationResponse
from .services.verifier_service import VerifierService, get_verifier_service


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or get_settings()
    
    # Initialize rate limiter
    limiter = Limiter(key_func=get_remote_address)
    
    app = FastAPI(title=cfg.project_name)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/verify", response_model=VerificationResponse)
    @limiter.limit("10/minute")
    async def verify(
        request: Request,
        form_payload: Annotated[str, Form(...)],
        image: Annotated[UploadFile, File(...)],
        service: VerifierService = Depends(get_verifier_service),
    ) -> VerificationResponse:
        try:
            payload_dict = json.loads(form_payload)
        except json.JSONDecodeError as exc:  # pragma: no cover - validated via FastAPI
            raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
        payload = VerificationPayload(**payload_dict)
        return await service.verify(payload, image)

    return app


app = create_app()
