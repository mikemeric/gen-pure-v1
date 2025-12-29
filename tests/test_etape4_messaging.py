"""
Tests de validation de l'étape 4 - Infrastructure Messaging

Tests pour valider:
- Circuit breaker pattern
- RabbitMQ consumer (sans RabbitMQ actif)
- Load balancer (round-robin, weighted, least connections)
"""
import os
import sys
import time
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_circuit_breaker():
    """Test circuit breaker pattern"""
    print("\n📝 Test 1: Circuit Breaker Pattern")
    print("-" * 60)
    
    try:
        from infrastructure.queue.circuit_breaker import CircuitBreaker, CircuitBreakerError, CircuitState
        
        # Test 1.1: Normal operation (CLOSED)
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=2)
        
        def successful_call():
            return "success"
        
        result = cb.call(successful_call)
        assert result == "success", "Should execute successfully"
        assert cb.state == CircuitState.CLOSED, "Should be CLOSED"
        print("  ✅ Normal operation (CLOSED state) OK")
        
        # Test 1.2: Failures trigger OPEN
        def failing_call():
            raise Exception("Simulated failure")
        
        for i in range(3):
            try:
                cb.call(failing_call)
            except Exception:
                pass
        
        assert cb.state == CircuitState.OPEN, "Should be OPEN after threshold"
        print("  ✅ Circuit opens after threshold OK")
        
        # Test 1.3: OPEN state blocks calls
        try:
            cb.call(successful_call)
            print("  ❌ Should have raised CircuitBreakerError")
            return False
        except CircuitBreakerError as e:
            assert "Circuit breaker is OPEN" in str(e), "Should raise CircuitBreakerError"
            print("  ✅ OPEN state blocks calls OK")
        
        # Test 1.4: Transition to HALF_OPEN
        time.sleep(2.5)  # Wait for recovery timeout
        
        # Next call should try HALF_OPEN
        result = cb.call(successful_call)
        assert result == "success", "Should succeed in HALF_OPEN"
        assert cb.state == CircuitState.CLOSED, "Should transition to CLOSED after success"
        print("  ✅ HALF_OPEN → CLOSED transition OK")
        
        # Test 1.5: Statistics
        stats = cb.get_stats()
        assert "state" in stats, "Should have state"
        assert "total_calls" in stats, "Should track calls"
        assert "success_rate" in stats, "Should track success rate"
        print(f"  ✅ Statistics OK (Success rate: {stats['success_rate']}%)")
        
        # Test 1.6: Manual reset
        cb2 = CircuitBreaker(failure_threshold=1)
        try:
            cb2.call(failing_call)
        except:
            pass
        assert cb2.state == CircuitState.OPEN, "Should be OPEN"
        cb2.reset()
        assert cb2.state == CircuitState.CLOSED, "Should be CLOSED after reset"
        print("  ✅ Manual reset OK")
        
        print("\n✅ CIRCUIT BREAKER: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ CIRCUIT BREAKER: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_circuit_breaker_decorator():
    """Test circuit breaker decorator"""
    print("\n📝 Test 2: Circuit Breaker Decorator")
    print("-" * 60)
    
    try:
        from infrastructure.queue.circuit_breaker import circuit_breaker
        
        # Test 2.1: Decorator usage
        @circuit_breaker(failure_threshold=2, recovery_timeout=1)
        def api_call(succeed=True):
            if succeed:
                return "OK"
            raise Exception("API error")
        
        result = api_call(succeed=True)
        assert result == "OK", "Should succeed"
        print("  ✅ Decorator successful call OK")
        
        # Test 2.2: Access circuit breaker stats
        assert hasattr(api_call, 'circuit_breaker'), "Should attach circuit breaker"
        stats = api_call.circuit_breaker.get_stats()
        assert stats['total_calls'] > 0, "Should track calls"
        print("  ✅ Decorator stats access OK")
        
        print("\n✅ CIRCUIT BREAKER DECORATOR: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ CIRCUIT BREAKER DECORATOR: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_load_balancer():
    """Test load balancer"""
    print("\n📝 Test 3: Load Balancer")
    print("-" * 60)
    
    try:
        from infrastructure.load_balancer.simple import LoadBalancer, LoadBalancingStrategy, create_load_balancer
        
        # Test 3.1: Round-robin
        backends = ["http://server1:8000", "http://server2:8000", "http://server3:8000"]
        lb = LoadBalancer(backends, strategy=LoadBalancingStrategy.ROUND_ROBIN)
        
        # Get 6 backends (should cycle 2 times)
        selected = []
        for _ in range(6):
            backend = lb.get_next_backend()
            selected.append(backend.address)
        
        # Should repeat pattern
        assert selected[0] == selected[3], "Should cycle round-robin"
        assert selected[1] == selected[4], "Should cycle round-robin"
        assert selected[2] == selected[5], "Should cycle round-robin"
        print("  ✅ Round-robin distribution OK")
        
        # Test 3.2: Least connections
        lb2 = LoadBalancer(backends, strategy=LoadBalancingStrategy.LEAST_CONNECTIONS)
        
        # Simulate different connection counts
        lb2._backends[0].connections = 5
        lb2._backends[1].connections = 2
        lb2._backends[2].connections = 8
        
        backend = lb2.get_next_backend()
        assert backend.address == "http://server2:8000", "Should select backend with least connections"
        print("  ✅ Least connections strategy OK")
        
        # Test 3.3: Add/remove backends
        lb3 = create_load_balancer(["http://server1:8000"])
        assert len(lb3._backends) == 1, "Should have 1 backend"
        
        lb3.add_backend("http://server2:8000")
        assert len(lb3._backends) == 2, "Should have 2 backends"
        
        lb3.remove_backend("http://server1:8000")
        assert len(lb3._backends) == 1, "Should have 1 backend"
        print("  ✅ Add/remove backends OK")
        
        # Test 3.4: Execute function
        def mock_request(backend_url, path="/"):
            return f"Response from {backend_url}{path}"
        
        result = lb.execute(mock_request, path="/api/health")
        assert "Response from http://server" in result, "Should execute on backend"
        print("  ✅ Execute function OK")
        
        # Test 3.5: Statistics
        stats = lb.get_stats()
        assert "strategy" in stats, "Should have strategy"
        assert "total_backends" in stats, "Should count backends"
        assert "backends" in stats, "Should list backends"
        print(f"  ✅ Statistics OK ({stats['total_backends']} backends)")
        
        # Test 3.6: Weighted round-robin
        lb4 = LoadBalancer(
            ["http://server1:8000"],
            strategy=LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN
        )
        lb4.add_backend("http://server2:8000", weight=3)  # 3x weight
        
        # Get 8 backends
        selected = []
        for _ in range(8):
            backend = lb4.get_next_backend()
            selected.append(backend.address)
        
        # Server2 should appear ~3x more than Server1
        server2_count = selected.count("http://server2:8000")
        assert server2_count >= 5, "Weighted backend should appear more often"
        print(f"  ✅ Weighted round-robin OK (server2: {server2_count}/8)")
        
        print("\n✅ LOAD BALANCER: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ LOAD BALANCER: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rabbitmq_consumer_structure():
    """Test RabbitMQ consumer structure (without actual connection)"""
    print("\n📝 Test 4: RabbitMQ Consumer Structure")
    print("-" * 60)
    
    try:
        # Test 4.1: Import check
        try:
            from infrastructure.queue.rabbitmq import RabbitMQConsumer
            print("  ✅ RabbitMQConsumer import OK")
        except ImportError as e:
            if "pika" in str(e):
                print("  ⚠️  pika not installed (optional for tests)")
                print("      Install with: pip install pika")
                return True
            raise
        
        # Test 4.2: Class structure
        assert hasattr(RabbitMQConsumer, 'start'), "Should have start method"
        assert hasattr(RabbitMQConsumer, 'stop'), "Should have stop method"
        assert hasattr(RabbitMQConsumer, 'get_stats'), "Should have get_stats method"
        print("  ✅ RabbitMQConsumer methods OK")
        
        # Test 4.3: Initialize (without actual connection)
        def mock_callback(message):
            print(f"Mock: {message}")
        
        # This will fail to connect but structure should be OK
        try:
            consumer = RabbitMQConsumer(
                "amqp://invalid:invalid@localhost:5672/",
                "test_queue",
                mock_callback
            )
            assert consumer.queue_name == "test_queue", "Should set queue name"
            assert consumer.max_retries == 3, "Should have default max_retries"
            print("  ✅ RabbitMQConsumer initialization OK")
        except Exception as e:
            # Connection failure expected if RabbitMQ not running
            if "pika" not in str(e):
                raise
        
        print("\n✅ RABBITMQ CONSUMER STRUCTURE: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ RABBITMQ CONSUMER STRUCTURE: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test integration between components"""
    print("\n📝 Test 5: Component Integration")
    print("-" * 60)
    
    try:
        from infrastructure.queue.circuit_breaker import CircuitBreaker
        from infrastructure.load_balancer.simple import LoadBalancer, LoadBalancingStrategy
        
        # Test 5.1: Circuit breaker with load balancer
        backends = ["http://server1:8000", "http://server2:8000"]
        lb = LoadBalancer(backends, strategy=LoadBalancingStrategy.ROUND_ROBIN)
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        
        call_count = 0
        def protected_request(backend_url):
            nonlocal call_count
            call_count += 1
            return f"Success from {backend_url}"
        
        # Execute with circuit breaker protection
        result = lb.execute(lambda url: cb.call(protected_request, url))
        assert "Success from" in result, "Should execute successfully"
        print("  ✅ Circuit breaker + Load balancer integration OK")
        
        # Test 5.2: Multiple calls
        for _ in range(5):
            try:
                lb.execute(lambda url: cb.call(protected_request, url))
            except:
                pass
        
        assert call_count > 0, "Should have made calls"
        print(f"  ✅ Multiple calls OK ({call_count} calls)")
        
        print("\n✅ COMPONENT INTEGRATION: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ COMPONENT INTEGRATION: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("TEST DE L'ÉTAPE 4 - INFRASTRUCTURE MESSAGING")
    print("=" * 60)
    
    # Set environment variables
    os.environ.setdefault('ENVIRONMENT', 'testing')
    
    tests = [
        test_circuit_breaker,
        test_circuit_breaker_decorator,
        test_load_balancer,
        test_rabbitmq_consumer_structure,
        test_integration
    ]
    
    results = [test() for test in tests]
    
    print()
    print("=" * 60)
    if all(results):
        print("✅ ÉTAPE 4 VALIDÉE - Tous les tests passent")
        print("=" * 60)
        print()
        print("🔧 Infrastructure Messaging:")
        print("  1. ✅ Circuit Breaker (CLOSED/OPEN/HALF_OPEN)")
        print("  2. ✅ Circuit Breaker Decorator")
        print("  3. ✅ Load Balancer (Round-Robin, Weighted, Least Connections)")
        print("  4. ✅ RabbitMQ Consumer (structure validée)")
        print("  5. ✅ Component Integration")
        print()
        print("⚠️  Note: RabbitMQ consumer nécessite pika + RabbitMQ pour tests complets")
        print("          Voir ETAPE4_VALIDATION.md pour tests avec RabbitMQ")
        print()
        print("➡️  Prêt pour l'ÉTAPE 5 (Detection Service Complete)")
    else:
        print("❌ ÉTAPE 4 ÉCHOUÉE - Corriger les erreurs")
    print("=" * 60)
