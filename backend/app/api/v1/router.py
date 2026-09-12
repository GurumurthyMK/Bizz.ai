"""API v1 route registration. Routers for later phases register here."""

from fastapi import APIRouter

from .routes.ai import router as ai_router
from .routes.alerts import router as alerts_router
from .routes.auth import router as auth_router
from .routes.campaigns import router as campaigns_router
from .routes.customers import router as customers_router
from .routes.data import router as data_router
from .routes.health import router as health_router
from .routes.intelligence import router as intelligence_router
from .routes.interactions import router as interactions_router
from .routes.opportunities import router as opportunities_router
from .routes.overview import router as overview_router
from .routes.predictions import router as predictions_router
from .routes.products import router as products_router
from .routes.reports import router as reports_router
from .routes.segments import router as segments_router
from .routes.transactions import router as transactions_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(ai_router)
router.include_router(alerts_router)
router.include_router(campaigns_router)
router.include_router(customers_router)
router.include_router(data_router)
router.include_router(health_router)
router.include_router(intelligence_router)
router.include_router(interactions_router)
router.include_router(opportunities_router)
router.include_router(overview_router)
router.include_router(predictions_router)
router.include_router(products_router)
router.include_router(reports_router)
router.include_router(segments_router)
router.include_router(transactions_router)

__all__ = ["router"]
