from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.chats import router as chats_router
from app.api.routes.events import router as events_router
from app.api.routes.groups import router as groups_router
from app.api.routes.memberships import router as memberships_router
from app.api.routes.payments import router as payments_router
from app.api.routes.users import router as users_router
from app.core.config import settings
from app.core.exceptions import AppException


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    debug=settings.DEBUG,
    description="Orbit backend starter for communities, groups, events, chats, and payments.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def handle_app_exception(_, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=dict(exc.headers or {}),
    )


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(groups_router)
app.include_router(memberships_router)
app.include_router(events_router)
app.include_router(chats_router)
app.include_router(payments_router)
