"""
Health Checker Initialization

Sets up periodic health checking for all services.

Usage:
    # In main.py or startup
    from services.health.startup import setup_health_checker
    
    @app.on_event("startup")
    async def startup():
        await setup_health_checker(app)
"""
from fastapi import FastAPI
from services.health import get_health_checker
from infrastructure.cache.redis_cache import get_cache
from core.logging import get_logger

logger = get_logger("health_startup")


async def setup_health_checker(app: FastAPI):
    """
    Initialize and start health checker.
    
    Registers all services for monitoring:
    - Redis cache
    - PostgreSQL database (if available)
    - Detector service (if available)
    
    Args:
        app: FastAPI application instance
    """
    logger.info("Setting up health checker...")
    
    # Get health checker instance
    checker = get_health_checker()
    
    # Register Redis cache
    try:
        cache = get_cache()
        checker.register_service("redis", cache.health_check)
        logger.info("Registered Redis cache for health monitoring")
    except Exception as e:
        logger.warning("Could not register Redis cache", error=str(e))
    
    # Register PostgreSQL (if available)
    try:
        from infrastructure.database.postgresql import get_database
        db = get_database()
        
        # Create health check function for PostgreSQL
        async def postgresql_health_check() -> bool:
            """Check PostgreSQL health"""
            try:
                # Simple query to verify connection
                async with db._pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                return True
            except Exception as e:
                logger.debug("PostgreSQL health check failed", error=str(e))
                return False
        
        checker.register_service("postgresql", postgresql_health_check)
        logger.info("Registered PostgreSQL for health monitoring")
    except Exception as e:
        logger.warning("Could not register PostgreSQL", error=str(e))
    
    # Register Detector service (if available)
    try:
        from services.detection.fuel_detector import get_detector
        detector = get_detector()
        
        # Create health check function for Detector
        async def detector_health_check() -> bool:
            """Check detector service health"""
            try:
                # Detector is healthy if initialized
                return detector is not None
            except Exception:
                return False
        
        checker.register_service("detector", detector_health_check)
        logger.info("Registered Detector for health monitoring")
    except Exception as e:
        logger.warning("Could not register Detector", error=str(e))
    
    # Start periodic health checks
    await checker.start()
    
    logger.info(
        "Health checker started",
        services=list(checker.services.keys()),
        interval=checker.interval
    )
    
    # Store in app state for cleanup
    app.state.health_checker = checker


async def shutdown_health_checker(app: FastAPI):
    """
    Stop health checker on shutdown.
    
    Args:
        app: FastAPI application instance
    """
    if hasattr(app.state, 'health_checker'):
        logger.info("Stopping health checker...")
        await app.state.health_checker.stop()
        logger.info("Health checker stopped")
