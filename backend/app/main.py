from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.limiter import limiter
from app.routers import auth, datasets, jobs, projects, ai, eda, cleaning, pipeline, training


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from app.services.storage_service import storage
        storage.ensure_bucket()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Could not ensure MinIO bucket at startup: %s", e)
    yield


app = FastAPI(title="AutoML API", version="1.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(datasets.router, prefix="/api/v1", tags=["datasets"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(eda.router, prefix="/api/v1/eda", tags=["eda"])
app.include_router(cleaning.router, prefix="/api/v1/cleaning", tags=["cleaning"])
app.include_router(pipeline.router, prefix="/api/v1", tags=["pipelines"])
app.include_router(training.router, prefix="/api/v1", tags=["training"])


@app.get("/health")
def health():
    return {"status": "ok"}
