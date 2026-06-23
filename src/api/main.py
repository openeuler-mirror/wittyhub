import logging
import sys
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import agents, health, index, skills
from src.core.config import get_settings

settings = get_settings()


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    structlog.get_logger().info("wittyhub starting up")
    yield
    structlog.get_logger().info("wittyhub shutting down")


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="WittyHub API",
        description="Agent and Skill Discovery Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(skills.router, prefix="/api/v1/skills")
    app.include_router(agents.router, prefix="/api/v1/agents")
    app.include_router(index.router, prefix="/api/v1/index")

    return app


app = create_app()