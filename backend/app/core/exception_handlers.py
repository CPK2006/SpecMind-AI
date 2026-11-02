from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    RequirementNotFoundError,
    ExtractedTextNotFoundError,
)
from app.core.logger import logger


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(RequirementNotFoundError)
    async def requirement_not_found_handler(
        request: Request,
        exc: RequirementNotFoundError,
    ):
        logger.error(
            "RequirementNotFoundError: %s | Path: %s",
            exc,
            request.url.path,
        )

        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": str(exc),
            },
        )

    @app.exception_handler(ExtractedTextNotFoundError)
    async def extracted_text_handler(
        request: Request,
        exc: ExtractedTextNotFoundError,
    ):
        logger.error(
            "ExtractedTextNotFoundError: %s | Path: %s",
            exc,
            request.url.path,
        )

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": str(exc),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ):
        logger.exception(
            "Unhandled exception occurred while processing %s",
            request.url.path,
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal Server Error",
            },
        )