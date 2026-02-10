"""
backend/main.py
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from routes import mcp
import logging

# Setup logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Debug: Print configuration on startup
logger.info("=" * 50)
logger.info("Backend Configuration:")
logger.info(f"Provider: {settings.provider}")
logger.info(f"Model: {settings.model}")
logger.info(f"Gemini API Key: {'✓' if settings.gemini_api_key else '✗'}")
logger.info(f"OpenAI API Key: {'✓' if settings.openai_api_key else '✗'}")
logger.info("=" * 50)

from routes.copilotkit_endpoint import setup_copilotkit

app = FastAPI(
    title="FastMCP Chat Server",
    description="MCP server",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"Validation error: {exc.errors()}", flush=True)
    print(f"Request body: {await request.body()}", flush=True)
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc)},
    )

app.include_router(mcp.router)

@app.on_event("startup")
async def startup_event():
    """Initialize CopilotKit on startup"""
    await setup_copilotkit(app)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "FastMCP Chat Server",
        "version": "0.1.0"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    from services.mcp_manager import mcp_manager
    
    mcps = await mcp_manager.list_mcps()
    
    return {
        "status": "healthy",
        "mcps_loaded": len(mcps),
        "backend": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        timeout_keep_alive=300,
        reload=True,
    )