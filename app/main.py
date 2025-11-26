"""
Main FastAPI application for ToS Monitor.
A serverless Terms of Service monitoring service that tracks legal document changes.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes import fetch_docs, tos
from app.storage import get_storage_client
from app.llm_client import get_llm_client

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ToS Monitor",
    description="A serverless Terms of Service monitoring service that automatically tracks changes in legal documents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(fetch_docs.router, tags=["Document Fetching"])
app.include_router(tos.router, tags=["ToS Documents"])


@app.get("/", response_model=Dict[str, Any])
async def root():
    """
    Root endpoint with service information.
    """
    return {
        "service": "ToS Monitor",
        "description": "Terms of Service monitoring service",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "sync": "POST /sync - Download and store legal documents",
            "list_tos": "GET /tos - List all ToS documents with version information",
            "get_tos": "GET /tos/{document_id} - Get detailed information for a specific ToS document",
            "get_tos_prev": "GET /tos/{document_id}/prev - Get plain text content of previous version of a ToS document",
            "get_tos_last": "GET /tos/{document_id}/last - Get plain text content of last version of a ToS document",
            "get_tos_date": "GET /tos/{document_id}/{date} - Get plain text content of specific dated version of a ToS document",
            "analyze_tos": "POST /tos/{document_id} - AI-powered document analysis",
            "health": "GET /health - Health check endpoint",
            "docs": "GET /docs - API documentation"
        }
    }


@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    Validates connectivity to required services.
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }

        # Check storage connectivity
        try:
            storage = get_storage_client()
            # Try to list files to verify connectivity
            await storage.list_files(prefix="", delimiter="/")
            health_status["checks"]["storage"] = {
                "status": "healthy",
                "message": "Cloud Storage connection successful"
            }
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["storage"] = {
                "status": "unhealthy",
                "message": f"Cloud Storage error: {str(e)}"
            }

        # Check LLM connectivity
        try:
            llm_client = get_llm_client()
            # Test connection
            connection_test = await llm_client.test_connection()
            if connection_test:
                health_status["checks"]["llm"] = {
                    "status": "healthy",
                    "message": "LLM service connection successful",
                    "model": llm_client.model
                }
            else:
                health_status["status"] = "unhealthy"
                health_status["checks"]["llm"] = {
                    "status": "unhealthy",
                    "message": "LLM service connection failed"
                }
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["llm"] = {
                "status": "unhealthy",
                "message": f"LLM service error: {str(e)}"
            }

        # Check environment variables
        required_env_vars = ["STORAGE_BUCKET", "OPENAI_API_KEY"]
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            health_status["status"] = "unhealthy"
            health_status["checks"]["environment"] = {
                "status": "unhealthy",
                "message": f"Missing required environment variables: {', '.join(missing_vars)}"
            }
        else:
            health_status["checks"]["environment"] = {
                "status": "healthy",
                "message": "All required environment variables present"
            }

        # Return appropriate status code
        status_code = 200 if health_status["status"] == "healthy" else 503

        return JSONResponse(
            content=health_status,
            status_code=status_code
        )

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            },
            status_code=503
        )


@app.get("/config", response_model=Dict[str, Any])
async def get_configuration():
    """
    Get current configuration information.
    """
    try:
        storage = get_storage_client()

        # Load document configuration
        config = await storage.load_config("documents.json")

        if not config:
            raise HTTPException(
                status_code=404,
                detail="Document configuration not found in storage"
            )

        # Get document count and summary
        documents = config.get("documents", [])

        return {
            "success": True,
            "configuration": {
                "document_count": len(documents),
                "documents": [
                    {
                        "id": doc.get("id", ""),
                        "name": doc.get("name", ""),
                        "url": doc.get("url", ""),
                        "has_selector": bool(doc.get("selector"))
                    }
                    for doc in documents
                ]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler.
    """
    logger.info("Starting ToS Monitor application")

    # Validate required environment variables based on storage mode
    storage_mode = os.getenv("STORAGE_MODE", "cloud").lower()
    required_vars = ["OPENAI_API_KEY"]
    missing_vars = []

    # Add storage-specific requirements
    if storage_mode == "cloud":
        required_vars.append("STORAGE_BUCKET")
    elif storage_mode == "local":
        # For local mode, no additional vars are required
        # LOCAL_STORAGE_PATH is optional and defaults to "./data"
        pass
    else:
        logger.error(f"Invalid STORAGE_MODE '{storage_mode}'. Must be 'local' or 'cloud'")
        raise RuntimeError(f"Invalid STORAGE_MODE '{storage_mode}'. Must be 'local' or 'cloud'")

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing_vars)}")

    logger.info(f"Using storage mode: {storage_mode}")
    if storage_mode == "local":
        local_path = os.getenv("LOCAL_STORAGE_PATH", "./data")
        logger.info(f"Local storage path: {local_path}")
    else:
        bucket_name = os.getenv("STORAGE_BUCKET")
        logger.info(f"Cloud storage bucket: {bucket_name}")

    logger.info("ToS Monitor application started successfully")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler.
    """
    logger.info("Shutting down ToS Monitor application")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )