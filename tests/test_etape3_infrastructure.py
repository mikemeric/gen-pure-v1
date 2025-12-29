"""
Tests de validation de l'étape 3 - Infrastructure Data Layer

Tests pour valider:
- Pool PostgreSQL thread-safe
- Models SQLAlchemy
- Repository pattern
- Cache Redis avec LRU fallback
"""
import os
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_lru_cache():
    """Test LRU cache in-memory"""
    print("\n📝 Test 1: LRU Cache (In-Memory)")
    print("-" * 60)
    
    try:
        from infrastructure.cache.redis_cache import LRUCache
        
        # Test 1.1: Basic get/set
        cache = LRUCache(max_size=3)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1", "Should get cached value"
        print("  ✅ Basic get/set OK")
        
        # Test 1.2: TTL expiration
        import time
        cache.set("key2", "value2", ttl=1)
        assert cache.get("key2") == "value2", "Should get value before expiry"
        time.sleep(1.1)
        assert cache.get("key2") is None, "Should return None after expiry"
        print("  ✅ TTL expiration OK")
        
        # Test 1.3: LRU eviction
        cache.set("a", "1")
        cache.set("b", "2")
        cache.set("c", "3")
        cache.set("d", "4")  # Should evict "a"
        assert cache.get("a") is None, "Oldest should be evicted"
        assert cache.get("b") == "2", "Newer should remain"
        print("  ✅ LRU eviction OK")
        
        # Test 1.4: Statistics
        stats = cache.get_stats()
        assert stats["type"] == "memory_lru", "Should be LRU cache"
        assert "hits" in stats, "Should track hits"
        assert "misses" in stats, "Should track misses"
        print(f"  ✅ Statistics OK (Hit rate: {stats['hit_rate']}%)")
        
        # Test 1.5: Clear
        cache.clear()
        assert cache.get("b") is None, "Cache should be empty after clear"
        print("  ✅ Clear OK")
        
        print("\n✅ LRU CACHE: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ LRU CACHE: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_redis_cache():
    """Test Redis cache with fallback"""
    print("\n📝 Test 2: Redis Cache (with LRU fallback)")
    print("-" * 60)
    
    try:
        from infrastructure.cache.redis_cache import RedisCache
        
        # Test 2.1: Initialize (without Redis URL = fallback to LRU)
        cache = RedisCache(redis_url=None)
        assert cache._using_redis == False, "Should use LRU fallback"
        print("  ✅ Initialization OK (LRU fallback)")
        
        # Test 2.2: Basic operations with LRU fallback
        cache.set("test_key", {"data": "test_value"})
        result = cache.get("test_key")
        assert result == {"data": "test_value"}, "Should cache complex objects"
        print("  ✅ Set/get complex objects OK")
        
        # Test 2.3: Delete
        assert cache.delete("test_key") == True, "Should delete existing key"
        assert cache.get("test_key") is None, "Deleted key should return None"
        print("  ✅ Delete OK")
        
        # Test 2.4: Exists
        cache.set("exists_key", "value")
        assert cache.exists("exists_key") == True, "Should detect existing key"
        assert cache.exists("nonexistent") == False, "Should detect missing key"
        print("  ✅ Exists check OK")
        
        # Test 2.5: Statistics
        stats = cache.get_stats()
        assert "type" in stats, "Should return stats"
        print(f"  ✅ Statistics OK ({stats['type']})")
        
        print("\n✅ REDIS CACHE: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ REDIS CACHE: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_models():
    """Test SQLAlchemy models"""
    print("\n📝 Test 3: SQLAlchemy Models")
    print("-" * 60)
    
    try:
        from infrastructure.database.models import User, Session, DetectionResult, ApiKey
        from datetime import datetime
        
        # Test 3.1: User model
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="$2b$12$...",
            full_name="Test User",
            roles=["user"],
            permissions=["detect"]
        )
        assert user.username == "testuser", "Should create user"
        assert user.roles == ["user"], "Should set roles"
        print("  ✅ User model OK")
        
        # Test 3.2: to_dict method
        user_dict = user.to_dict()
        assert "username" in user_dict, "Should convert to dict"
        assert user_dict["username"] == "testuser", "Should include data"
        print("  ✅ Model to_dict OK")
        
        # Test 3.3: DetectionResult model
        detection = DetectionResult(
            user_id=1,
            niveau_percentage=75.5,
            confiance=0.92,
            methode_utilisee="clustering",
            temps_traitement_ms=150.0
        )
        assert detection.niveau_percentage == 75.5, "Should create detection result"
        print("  ✅ DetectionResult model OK")
        
        # Test 3.4: Session model
        session = Session(
            user_id=1,
            refresh_token_hash="hash123",
            expires_at=datetime.utcnow(),
            ip_address="192.168.1.1"
        )
        assert session.user_id == 1, "Should create session"
        print("  ✅ Session model OK")
        
        # Test 3.5: ApiKey model
        api_key = ApiKey(
            user_id=1,
            key_hash="keyhash123",
            key_prefix="proj_abc",
            name="My API Key",
            permissions=["detect"]
        )
        assert api_key.name == "My API Key", "Should create API key"
        print("  ✅ ApiKey model OK")
        
        print("\n✅ MODELS: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ MODELS: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_repository_pattern():
    """Test repository pattern (without database)"""
    print("\n📝 Test 4: Repository Pattern")
    print("-" * 60)
    
    try:
        from infrastructure.database.repositories import BaseRepository, UserRepository
        
        # Test 4.1: Import successful
        assert BaseRepository is not None, "Should import BaseRepository"
        assert UserRepository is not None, "Should import UserRepository"
        print("  ✅ Repository imports OK")
        
        # Test 4.2: Repository structure
        # Note: Can't fully test without DB connection, but can verify class structure
        assert hasattr(BaseRepository, 'create'), "Should have create method"
        assert hasattr(BaseRepository, 'get'), "Should have get method"
        assert hasattr(BaseRepository, 'update'), "Should have update method"
        assert hasattr(BaseRepository, 'delete'), "Should have delete method"
        print("  ✅ BaseRepository methods OK")
        
        # Test 4.3: UserRepository specific methods
        assert hasattr(UserRepository, 'get_by_username'), "Should have get_by_username"
        assert hasattr(UserRepository, 'get_by_email'), "Should have get_by_email"
        assert hasattr(UserRepository, 'authenticate'), "Should have authenticate"
        print("  ✅ UserRepository methods OK")
        
        print("\n✅ REPOSITORY PATTERN: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ REPOSITORY PATTERN: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_integration():
    """Test cache with singleton pattern"""
    print("\n📝 Test 5: Cache Integration (Singleton)")
    print("-" * 60)
    
    try:
        from infrastructure.cache.redis_cache import get_cache
        
        # Test 5.1: Singleton
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2, "Should return same instance"
        print("  ✅ Singleton pattern OK")
        
        # Test 5.2: Cache operations
        cache1.set("integration_test", {"value": 123}, ttl=60)
        result = cache2.get("integration_test")
        assert result == {"value": 123}, "Singleton should share data"
        print("  ✅ Shared cache state OK")
        
        # Test 5.3: Cache stats
        stats = cache1.get_stats()
        assert stats is not None, "Should return stats"
        print(f"  ✅ Cache stats OK: {stats.get('type', 'unknown')}")
        
        print("\n✅ CACHE INTEGRATION: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ CACHE INTEGRATION: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("TEST DE L'ÉTAPE 3 - INFRASTRUCTURE DATA LAYER")
    print("=" * 60)
    
    # Set environment variables
    os.environ.setdefault('ENVIRONMENT', 'testing')
    
    tests = [
        test_lru_cache,
        test_redis_cache,
        test_models,
        test_repository_pattern,
        test_cache_integration
    ]
    
    results = [test() for test in tests]
    
    print()
    print("=" * 60)
    if all(results):
        print("✅ ÉTAPE 3 VALIDÉE - Tous les tests passent")
        print("=" * 60)
        print()
        print("🗄️  Infrastructure Data Layer:")
        print("  1. ✅ LRU Cache (in-memory)")
        print("  2. ✅ Redis Cache (with fallback)")
        print("  3. ✅ SQLAlchemy Models (User, Session, DetectionResult, ApiKey)")
        print("  4. ✅ Repository Pattern (Base + User)")
        print("  5. ✅ Cache Integration (singleton)")
        print()
        print("⚠️  Note: Pool PostgreSQL nécessite une DB pour tests complets")
        print("          Voir ETAPE3_VALIDATION.md pour tests avec DB")
        print()
        print("➡️  Prêt pour l'ÉTAPE 4 (Infrastructure - Messaging)")
    else:
        print("❌ ÉTAPE 3 ÉCHOUÉE - Corriger les erreurs")
    print("=" * 60)
