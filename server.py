"""
MCP Server - FastAPI Application

This is the main entry point for the Model Context Protocol server.
It exposes HTTP endpoints for context orchestration and tool execution.

Business logic is delegated to the executor module - this file only handles:
- API routing
- Request/response handling
- Middleware configuration
- Health checks
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from config import config
from registry.schemas import ExecuteRequest, ExecuteResponse, HealthResponse
from executor.execute import execute_context_request


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.server.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler for startup/shutdown events.

    Initializes connections and validates configuration on startup.
    Cleans up resources on shutdown.
    """
    # Startup
    logger.info("Starting MCP Server...")

    # Validate configuration
    warnings = config.validate()
    for warning in warnings:
        logger.warning(f"Config warning: {warning}")

    logger.info(f"Server configured for {config.llm.provider} LLM provider")
    logger.info(f"Debug mode: {config.server.debug}")

    yield

    # Shutdown
    logger.info("Shutting down MCP Server...")


# Initialize FastAPI application
app = FastAPI(
    title="Context Hub MCP Server",
    description="Model Context Protocol server for AI agent context orchestration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if config.server.debug else None,
    redoc_url="/redoc" if config.server.debug else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.server.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint for container orchestration.

    Returns:
        HealthResponse with server status
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        llm_provider=config.llm.gemini_model
    )


@app.post("/execute", response_model=ExecuteResponse, tags=["Execution"])
async def execute(request: ExecuteRequest) -> ExecuteResponse:
    """
    Main execution endpoint for MCP context requests.

    Accepts a user message and context identifiers, orchestrates tool execution,
    memory retrieval, and LLM processing to produce a contextual response.

    Args:
        request: ExecuteRequest containing user_id, channel_id, and message

    Returns:
        ExecuteResponse with the processed result and metadata

    Raises:
        HTTPException: On validation or processing errors
    """
    logger.info(
        f"Execute request: user={request.user_id}, "
        f"channel={request.channel_id}, "
        f"message_length={len(request.message)}"
    )

    try:
        response = await execute_context_request(
            user_id=request.user_id,
            channel_id=request.channel_id,
            message=request.message,
            metadata=request.metadata
        )

        logger.info(
            f"Execute completed: tools_used={response.tools_used}, "
            f"success={response.success}"
        )

        return response

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"Access denied: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Execution error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during execution"
        )


@app.get("/", tags=["System"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "service": "Context Hub MCP Server",
        "version": "1.0.0",
        "docs": "/docs" if config.server.debug else "Disabled in production"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug,
        log_level=config.server.log_level.lower()
    )
