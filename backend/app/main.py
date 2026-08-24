import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.routes.tasks import router as tasks_router
from app.routes.experiments import router as experiments_router
from app.routes.results import router as results_router
from app.routes.models import router as models_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("mast_lab")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing MAST Topology Lab database & benchmark tasks...")
    init_db()
    logger.info("MAST Topology Lab backend started successfully.")
    yield
    logger.info("MAST Topology Lab backend shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Experimental research platform for analyzing multi-agent LLM communication topologies, network metrics, and failure modes.",
    lifespan=lifespan
)

# CORS Configuration
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include API Routers
app.include_router(tasks_router)
app.include_router(experiments_router)
app.include_router(results_router)
app.include_router(models_router)


@app.get("/health")
def health_check():
    agent_configs = settings.get_all_agent_configs()
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "mock_mode": settings.is_mock_enabled,
        "agent_models": [
            {"agent": a.agent_id, "role": a.role, "model": a.model, "provider": a.provider, "is_local": a.is_local}
            for a in agent_configs
        ]
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"An unexpected server error occurred: {str(exc)}"}
    )
