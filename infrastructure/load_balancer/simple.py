"""
Simple load balancer with multiple strategies

Provides load balancing across multiple backend servers:
- Round-robin distribution
- Weighted round-robin
- Health checks
- Automatic backend removal on failure
"""
import threading
from typing import List, Callable, Any, Optional, Dict
from enum import Enum


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"


class Backend:
    """
    Backend server representation
    
    Attributes:
        address: Server address
        weight: Weight for weighted round-robin
        is_healthy: Health status
        connections: Current connection count
    """
    
    def __init__(self, address: str, weight: int = 1):
        """
        Initialize backend
        
        Args:
            address: Server address (e.g., "http://localhost:8001")
            weight: Weight for weighted distribution (default: 1)
        """
        self.address = address
        self.weight = weight
        self.is_healthy = True
        self.connections = 0
        self._total_requests = 0
        self._failed_requests = 0
    
    def increment_connections(self):
        """Increment active connections"""
        self.connections += 1
        self._total_requests += 1
    
    def decrement_connections(self):
        """Decrement active connections"""
        self.connections = max(0, self.connections - 1)
    
    def record_failure(self):
        """Record a failed request"""
        self._failed_requests += 1
    
    def get_stats(self) -> dict:
        """Get backend statistics"""
        success_rate = 0
        if self._total_requests > 0:
            success_rate = (
                (self._total_requests - self._failed_requests) /
                self._total_requests * 100
            )
        
        return {
            "address": self.address,
            "weight": self.weight,
            "is_healthy": self.is_healthy,
            "connections": self.connections,
            "total_requests": self._total_requests,
            "failed_requests": self._failed_requests,
            "success_rate": round(success_rate, 2)
        }


class LoadBalancer:
    """
    Simple load balancer with multiple strategies
    
    Features:
    - Round-robin distribution
    - Weighted round-robin
    - Least connections
    - Health checks
    - Automatic backend removal
    - Thread-safe
    """
    
    def __init__(
        self,
        backends: List[str],
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
        health_check_fn: Optional[Callable[[str], bool]] = None
    ):
        """
        Initialize load balancer
        
        Args:
            backends: List of backend addresses
            strategy: Load balancing strategy
            health_check_fn: Optional function to check backend health
        
        Example:
            >>> lb = LoadBalancer(
            ...     ["http://localhost:8001", "http://localhost:8002"],
            ...     strategy=LoadBalancingStrategy.ROUND_ROBIN
            ... )
        """
        self.strategy = strategy
        self.health_check_fn = health_check_fn
        
        # Initialize backends
        self._backends: List[Backend] = [
            Backend(address) for address in backends
        ]
        
        # Round-robin index
        self._current_index = 0
        self._lock = threading.Lock()
        
        # Statistics
        self._total_requests = 0
    
    def add_backend(self, address: str, weight: int = 1):
        """
        Add a new backend
        
        Args:
            address: Backend address
            weight: Backend weight
        """
        with self._lock:
            backend = Backend(address, weight)
            self._backends.append(backend)
            print(f"➕ Added backend: {address} (weight: {weight})")
    
    def remove_backend(self, address: str):
        """
        Remove a backend
        
        Args:
            address: Backend address to remove
        """
        with self._lock:
            self._backends = [
                b for b in self._backends
                if b.address != address
            ]
            print(f"➖ Removed backend: {address}")
    
    def get_next_backend(self) -> Optional[Backend]:
        """
        Get next backend according to strategy
        
        Returns:
            Backend: Next backend or None if no healthy backends
        
        Raises:
            RuntimeError: If no healthy backends available
        """
        with self._lock:
            self._total_requests += 1
            
            # Filter healthy backends
            healthy_backends = [b for b in self._backends if b.is_healthy]
            
            if not healthy_backends:
                raise RuntimeError("No healthy backends available")
            
            # Select backend based on strategy
            if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
                return self._round_robin(healthy_backends)
            
            elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
                return self._weighted_round_robin(healthy_backends)
            
            elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
                return self._least_connections(healthy_backends)
            
            else:
                return self._round_robin(healthy_backends)
    
    def _round_robin(self, backends: List[Backend]) -> Backend:
        """
        Round-robin selection
        
        Args:
            backends: List of healthy backends
        
        Returns:
            Backend: Selected backend
        """
        backend = backends[self._current_index % len(backends)]
        self._current_index += 1
        return backend
    
    def _weighted_round_robin(self, backends: List[Backend]) -> Backend:
        """
        Weighted round-robin selection
        
        Args:
            backends: List of healthy backends
        
        Returns:
            Backend: Selected backend
        """
        # Build weighted list
        weighted_backends = []
        for backend in backends:
            weighted_backends.extend([backend] * backend.weight)
        
        if not weighted_backends:
            return backends[0]
        
        backend = weighted_backends[self._current_index % len(weighted_backends)]
        self._current_index += 1
        return backend
    
    def _least_connections(self, backends: List[Backend]) -> Backend:
        """
        Least connections selection
        
        Args:
            backends: List of healthy backends
        
        Returns:
            Backend: Backend with fewest connections
        """
        return min(backends, key=lambda b: b.connections)
    
    def execute(self, func: Callable[[str], Any], *args, **kwargs) -> Any:
        """
        Execute function on selected backend
        
        Args:
            func: Function to execute (receives backend address as first arg)
            *args: Additional arguments
            **kwargs: Additional keyword arguments
        
        Returns:
            Any: Function result
        
        Raises:
            RuntimeError: If all backends fail
        
        Example:
            >>> def make_request(backend_url, path):
            ...     return requests.get(f"{backend_url}{path}")
            >>> 
            >>> result = lb.execute(make_request, "/api/health")
        """
        attempts = 0
        max_attempts = len(self._backends)
        
        while attempts < max_attempts:
            try:
                # Get backend
                backend = self.get_next_backend()
                backend.increment_connections()
                
                try:
                    # Execute function
                    result = func(backend.address, *args, **kwargs)
                    return result
                
                finally:
                    backend.decrement_connections()
            
            except Exception as e:
                # Record failure
                if 'backend' in locals():
                    backend.record_failure()
                
                attempts += 1
                
                # Check health if function provided
                if self.health_check_fn and 'backend' in locals():
                    if not self.health_check_fn(backend.address):
                        backend.is_healthy = False
                        print(f"❌ Backend unhealthy: {backend.address}")
                
                # Retry with next backend
                if attempts < max_attempts:
                    continue
                else:
                    raise RuntimeError(f"All backends failed: {e}")
    
    def check_health(self):
        """
        Perform health checks on all backends
        
        Uses health_check_fn if provided, otherwise marks all as healthy.
        """
        if not self.health_check_fn:
            return
        
        with self._lock:
            for backend in self._backends:
                try:
                    is_healthy = self.health_check_fn(backend.address)
                    
                    # Status change
                    if backend.is_healthy != is_healthy:
                        status = "✅ healthy" if is_healthy else "❌ unhealthy"
                        print(f"Backend {backend.address}: {status}")
                    
                    backend.is_healthy = is_healthy
                
                except Exception as e:
                    print(f"❌ Health check failed for {backend.address}: {e}")
                    backend.is_healthy = False
    
    def get_stats(self) -> dict:
        """
        Get load balancer statistics
        
        Returns:
            dict: Statistics including backend stats, strategy, etc.
        """
        with self._lock:
            backends_stats = [b.get_stats() for b in self._backends]
            healthy_count = sum(1 for b in self._backends if b.is_healthy)
            
            return {
                "strategy": self.strategy.value,
                "total_backends": len(self._backends),
                "healthy_backends": healthy_count,
                "total_requests": self._total_requests,
                "backends": backends_stats
            }


# Convenience function for quick setup
def create_load_balancer(
    backends: List[str],
    strategy: str = "round_robin"
) -> LoadBalancer:
    """
    Create a load balancer with string strategy
    
    Args:
        backends: List of backend addresses
        strategy: Strategy name ("round_robin", "weighted_round_robin", "least_connections")
    
    Returns:
        LoadBalancer: Configured load balancer
    
    Example:
        >>> lb = create_load_balancer(
        ...     ["http://server1:8000", "http://server2:8000"],
        ...     strategy="round_robin"
        ... )
    """
    strategy_map = {
        "round_robin": LoadBalancingStrategy.ROUND_ROBIN,
        "weighted_round_robin": LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN,
        "least_connections": LoadBalancingStrategy.LEAST_CONNECTIONS
    }
    
    strategy_enum = strategy_map.get(strategy, LoadBalancingStrategy.ROUND_ROBIN)
    
    return LoadBalancer(backends, strategy=strategy_enum)
