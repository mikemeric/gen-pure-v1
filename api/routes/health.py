"""
Health check routes

Provides health status endpoints:
- GET /health/         → Simple health check
- GET /health/detailed → Detailed health with all services
"""
from fastapi import APIRouter
from services.health import get_health_checker

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
async def health_check():
    """
    Simple health check endpoint.
    
    Returns:
        dict: Basic health status
    
    Example:
        >>> GET /api/health/
        {"status": "healthy"}
    """
    checker = get_health_checker()
    is_healthy = checker.is_system_healthy()
    
    return {
        "status": "healthy" if is_healthy else "unhealthy"
    }


@router.get("/detailed")
async def detailed_health():
    """
    Detailed health check endpoint.
    
    Returns complete health status for all registered services:
    - Redis cache
    - PostgreSQL database
    - Fuel detector
    - Individual service metrics
    
    Returns:
        dict: Detailed health information
    
    Example:
        >>> GET /api/health/detailed
        {
            "status": "healthy",
            "services": {
                "redis": {
                    "status": "healthy",
                    "last_check": "2024-12-14T10:30:00",
                    "success_rate": 98.5,
                    ...
                },
                "postgresql": {...},
                "detector": {...}
            },
            "summary": {
                "total": 3,
                "healthy": 3,
                "unhealthy": 0
            }
        }
    """
    checker = get_health_checker()
    
    # Get health status for all services
    health_status = checker.get_health_status()
    
    # Overall system health
    is_healthy = checker.is_system_healthy()
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        **health_status
    }
