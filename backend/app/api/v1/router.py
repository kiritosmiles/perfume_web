from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.config import router as config_router
from app.api.v1.health import router as health_router
from app.api.v1.guest import router as guest_router
from app.api.v1.share import router as share_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(config_router)
router.include_router(health_router)
router.include_router(guest_router)
router.include_router(share_router)
