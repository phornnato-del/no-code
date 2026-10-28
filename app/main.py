import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    client = AsyncMongoClient(
        settings.mongodb_url,
        serverSelectionTimeoutMS=3000,
    )
    app.state.mongo_client = client
    app.state.database = client[settings.mongodb_database]
    try:
        yield
    finally:
        await client.close()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="REST API foundation for the WebBuilder platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health/live", tags=["health"])
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
async def readiness(request: Request) -> JSONResponse:
    try:
        await request.app.state.mongo_client.admin.command("ping")
    except PyMongoError:
        logger.exception("MongoDB readiness check failed")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "dependencies": {"mongodb": "unavailable"},
            },
        )

    return JSONResponse(
        content={
            "status": "ready",
            "dependencies": {"mongodb": "available"},
        }
    )
