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
    level_name = settings.logging.level.strip().upper()
    level = getattr(logging, level_name, logging.INFO)

    # Use logging.level as the single switch for standard Python, Uvicorn,
    # application, and third-party loggers that already exist at startup.
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    if not root_logger.handlers:
        root_handler = logging.StreamHandler(sys.stdout)
        root_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s"
            )
        )
        root_logger.addHandler(root_handler)
    for handler in root_logger.handlers:
        handler.setLevel(level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.setLevel(level)
        for handler in uvicorn_logger.handlers:
            handler.setLevel(level)

    for registered_logger in logging.Logger.manager.loggerDict.values():
        if not isinstance(registered_logger, logging.Logger):
            continue
        registered_logger.setLevel(level)
        for handler in registered_logger.handlers:
            handler.setLevel(level)

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = structlog.get_logger()
    logger.info("wittyhub starting up")

    collector = None
    if settings.security.enable_audit:
        from src.security.detector import start_skillspector_collector

        collector = await start_skillspector_collector()

    yield

    if collector is not None:
        await collector.stop()
    logger.info("wittyhub shutting down")


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
