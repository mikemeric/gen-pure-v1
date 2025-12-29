"""
Health Checker Service

Monitors system health with periodic checks:
- Redis connection
- PostgreSQL connection
- Detector service
- Cache performance

Features:
- Periodic checks (configurable interval)
- Auto-reconnection on failures
- Structured logging
- Health status tracking
"""
import asyncio
from typing import Dict, Callable, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

from core.logging import get_logger

logger = get_logger("health_checker")


class HealthStatus(Enum):
    """Health status for services"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    """Health information for a single service"""
    name: str
    status: HealthStatus
    last_check: datetime
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    error_message: Optional[str] = None
    check_count: int = 0
    failure_count: int = 0
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "status": self.status.value,
            "last_check": self.last_check.isoformat(),
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "error_message": self.error_message,
            "check_count": self.check_count,
            "failure_count": self.failure_count,
            "success_rate": (
                (self.check_count - self.failure_count) / self.check_count * 100
                if self.check_count > 0 else 0.0
            ),
            "metadata": self.metadata
        }


class HealthChecker:
    """
    Periodic health checker for all system services.
    
    Features:
    - Configurable check interval
    - Per-service health functions
    - Auto-reconnection attempts
    - Structured logging
    - Health history tracking
    
    Usage:
        checker = HealthChecker(interval_seconds=30)
        checker.register_service("redis", redis_cache.health_check)
        checker.register_service("postgresql", db.health_check)
        await checker.start()
    """
    
    def __init__(self, interval_seconds: int = 30):
        """
        Initialize health checker.
        
        Args:
            interval_seconds: Time between health checks (default: 30s)
        """
        self.interval = interval_seconds
        self.services: Dict[str, Callable] = {}
        self.health_status: Dict[str, ServiceHealth] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        logger.info("HealthChecker initialized", interval=interval_seconds)
    
    def register_service(self, name: str, health_check_func: Callable) -> None:
        """
        Register a service for health monitoring.
        
        Args:
            name: Service name (e.g., "redis", "postgresql")
            health_check_func: Async function that returns bool (True if healthy)
        
        Example:
            >>> checker.register_service("redis", redis_cache.health_check)
            >>> checker.register_service("postgresql", db.health_check)
        """
        self.services[name] = health_check_func
        
        # Initialize health status
        self.health_status[name] = ServiceHealth(
            name=name,
            status=HealthStatus.UNKNOWN,
            last_check=datetime.now()
        )
        
        logger.info("Service registered", service=name)
    
    async def check_service(self, name: str) -> bool:
        """
        Check health of a single service.
        
        Args:
            name: Service name
            
        Returns:
            bool: True if healthy, False otherwise
        """
        if name not in self.services:
            logger.error("Service not registered", service=name)
            return False
        
        health_func = self.services[name]
        health_info = self.health_status[name]
        
        now = datetime.now()
        health_info.last_check = now
        health_info.check_count += 1
        
        try:
            # Call health check function
            is_healthy = await health_func()
            
            if is_healthy:
                health_info.status = HealthStatus.HEALTHY
                health_info.last_success = now
                health_info.error_message = None
                
                logger.debug("Service healthy", service=name)
                return True
            
            else:
                health_info.status = HealthStatus.UNHEALTHY
                health_info.last_failure = now
                health_info.failure_count += 1
                health_info.error_message = "Health check returned False"
                
                logger.warning(
                    "Service unhealthy",
                    service=name,
                    failure_count=health_info.failure_count
                )
                return False
        
        except Exception as e:
            health_info.status = HealthStatus.UNHEALTHY
            health_info.last_failure = now
            health_info.failure_count += 1
            health_info.error_message = str(e)
            
            logger.error(
                "Service health check failed",
                service=name,
                error=str(e),
                failure_count=health_info.failure_count
            )
            return False
    
    async def check_all_services(self) -> Dict[str, bool]:
        """
        Check health of all registered services.
        
        Returns:
            Dict[str, bool]: Service name -> health status
        """
        results = {}
        
        for name in self.services.keys():
            results[name] = await self.check_service(name)
        
        return results
    
    async def _periodic_check_loop(self):
        """Main loop for periodic health checks"""
        logger.info("Health check loop started", interval=self.interval)
        
        while self._running:
            try:
                # Check all services
                results = await self.check_all_services()
                
                # Log summary
                healthy_count = sum(1 for h in results.values() if h)
                total_count = len(results)
                
                if healthy_count == total_count:
                    logger.info(
                        "All services healthy",
                        healthy=healthy_count,
                        total=total_count
                    )
                else:
                    unhealthy = [
                        name for name, healthy in results.items()
                        if not healthy
                    ]
                    logger.warning(
                        "Some services unhealthy",
                        healthy=healthy_count,
                        total=total_count,
                        unhealthy_services=unhealthy
                    )
                
                # Wait for next check
                await asyncio.sleep(self.interval)
            
            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            
            except Exception as e:
                logger.error("Error in health check loop", error=str(e))
                await asyncio.sleep(self.interval)
    
    async def start(self):
        """Start periodic health checks"""
        if self._running:
            logger.warning("Health checker already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._periodic_check_loop())
        
        logger.info("Health checker started")
    
    async def stop(self):
        """Stop periodic health checks"""
        if not self._running:
            logger.warning("Health checker not running")
            return
        
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health checker stopped")
    
    def get_health_status(self, name: Optional[str] = None) -> Dict:
        """
        Get health status for service(s).
        
        Args:
            name: Service name (None for all services)
            
        Returns:
            Dict: Health status information
        """
        if name:
            if name not in self.health_status:
                return {
                    "error": f"Service '{name}' not registered"
                }
            
            return self.health_status[name].to_dict()
        
        # Return all services
        return {
            "services": {
                name: info.to_dict()
                for name, info in self.health_status.items()
            },
            "summary": {
                "total": len(self.health_status),
                "healthy": sum(
                    1 for info in self.health_status.values()
                    if info.status == HealthStatus.HEALTHY
                ),
                "unhealthy": sum(
                    1 for info in self.health_status.values()
                    if info.status == HealthStatus.UNHEALTHY
                ),
                "unknown": sum(
                    1 for info in self.health_status.values()
                    if info.status == HealthStatus.UNKNOWN
                )
            }
        }
    
    def is_system_healthy(self) -> bool:
        """
        Check if entire system is healthy.
        
        Returns:
            bool: True if all services are healthy
        """
        return all(
            info.status == HealthStatus.HEALTHY
            for info in self.health_status.values()
        )


# Singleton instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """
    Get the global health checker instance.
    
    Returns:
        HealthChecker: Global instance
    """
    global _health_checker
    
    if _health_checker is None:
        from core.config import get_config
        config = get_config()
        
        # Create with configurable interval (default 30s)
        interval = getattr(config, 'health_check_interval', 30)
        _health_checker = HealthChecker(interval_seconds=interval)
    
    return _health_checker
