"""
Main FastAPI application for ToS Monitor.
A serverless Terms of Service monitoring service that tracks legal document changes.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes import fetch_docs, generate_diffs, get_diffs
from app.storage import get_storage_client
from app.llm_client import get_llm_client


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
app.include_router(generate_diffs.router, tags=["Diff Generation"])
app.include_router(get_diffs.router, tags=["Diff Retrieval"])


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
            "fetch_docs": "POST /fetch-docs - Download and store legal documents",
            "generate_diffs": "POST /generate-diffs - Generate LLM-powered document comparisons",
            "list_diffs": "GET /diffs - List all documents and their diff status",
            "get_diff": "GET /diffs/{document_id} - Get latest diff for a document",
            "get_diff_history": "GET /diffs/{document_id}/history - Get diff history",
            "get_specific_diff": "GET /diffs/{document_id}/{timestamp} - Get specific diff by timestamp",
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
            },
            "environment": {
                "storage_bucket": os.getenv("STORAGE_BUCKET", ""),
                "llm_model": os.getenv("LLM_MODEL", "gpt-4-turbo-preview"),
                "has_openai_key": bool(os.getenv("OPENAI_API_KEY"))
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

    # Validate required environment variables
    required_vars = ["STORAGE_BUCKET", "OPENAI_API_KEY"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing_vars)}")

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