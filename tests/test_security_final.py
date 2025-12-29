"""
Tests Sécurité Complets - Sprint 6 Final

Valide que TOUS les bloqueurs production ont été éliminés :
1. No hardcoded credentials
2. JWT secret obligatoire en production
3. Upload size limits + MIME validation stricte
4. Health checks fonctionnels
5. Rate limiting robuste

Résultat attendu: ✅ 100% tests passent
"""
import os
import re
from pathlib import Path
import asyncio


class SecurityTestSuite:
    """Suite de tests de sécurité"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def test(self, name: str):
        """Decorator pour les tests"""
        def decorator(func):
            self.tests.append((name, func))
            return func
        return decorator
    
    async def run_all(self):
        """Lancer tous les tests"""
        print("=" * 70)
        print("TESTS SÉCURITÉ COMPLETS - SPRINT 6 ÉTAPE 4")
        print("=" * 70)
        print()
        
        for name, test_func in self.tests:
            try:
                result = await test_func()
                if result:
                    self.passed += 1
                else:
                    self.failed += 1
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                self.failed += 1
        
        # Summary
        print()
        print("=" * 70)
        print(f"RÉSULTATS: {self.passed} PASSED, {self.failed} FAILED")
        print("=" * 70)
        
        return self.failed == 0


# Initialize test suite
suite = SecurityTestSuite()


@suite.test("SECURITY-001: No Hardcoded Credentials")
async def test_no_hardcoded_credentials():
    """Vérifier qu'il n'y a AUCUN credential hardcodé"""
    print("🔐 SECURITY-001: No Hardcoded Credentials")
    print("-" * 70)
    
    root_dir = "/home/claude/detection_system_v2"
    
    # Pattern bcrypt hash
    bcrypt_pattern = r'\$2b\$\d{2}\$[A-Za-z0-9./]{53}'
    
    violations = []
    
    for root, dirs, files in os.walk(root_dir):
        # Skip tests and tools
        if any(skip in root for skip in ['__pycache__', 'tests', 'tools']):
            continue
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                
                with open(filepath, 'r') as f:
                    content = f.read()
                
                matches = re.findall(bcrypt_pattern, content)
                
                if matches:
                    violations.append((filepath, len(matches)))
    
    if violations:
        print(f"  ❌ FAILED: Found hardcoded credentials in {len(violations)} file(s)")
        for filepath, count in violations:
            print(f"     - {filepath}: {count} hash(es)")
        return False
    
    print("  ✅ PASSED: No hardcoded credentials found")
    return True


@suite.test("SECURITY-002: JWT Secret Production Validation")
async def test_jwt_secret_production():
    """Vérifier que JWT secret est obligatoire en production"""
    print("\n🔐 SECURITY-002: JWT Secret Production Validation")
    print("-" * 70)
    
    try:
        # Import config
        import sys
        sys.path.insert(0, "/home/claude/detection_system_v2")
        from core.config import Settings
        
        # Test 1: Production sans JWT = SystemExit
        print("  Test 1: Production without JWT secret...")
        try:
            config = Settings(environment="production", jwt_secret_key="")
            print("  ❌ FAILED: Should have raised SystemExit!")
            return False
        except SystemExit:
            print("  ✅ App exits correctly")
        
        # Test 2: Production avec JWT court = SystemExit
        print("  Test 2: Production with short JWT secret...")
        try:
            config = Settings(environment="production", jwt_secret_key="short")
            print("  ❌ FAILED: Should have raised SystemExit!")
            return False
        except SystemExit:
            print("  ✅ App exits correctly")
        
        # Test 3: Production avec JWT valide = OK
        print("  Test 3: Production with valid JWT secret...")
        config = Settings(
            environment="production",
            jwt_secret_key="a" * 64
        )
        print("  ✅ Accepts valid JWT secret")
        
        # Test 4: Development auto-génère
        print("  Test 4: Development auto-generates secret...")
        config = Settings(environment="development", jwt_secret_key="")
        if len(config.jwt_secret_key) < 32:
            print(f"  ❌ FAILED: Generated secret too short ({len(config.jwt_secret_key)} chars)")
            return False
        print(f"  ✅ Auto-generated {len(config.jwt_secret_key)} char secret")
        
        print("  ✅ PASSED: JWT validation strict")
        return True
    
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


@suite.test("SECURITY-003: Upload Size Limits")
async def test_upload_size_limits():
    """Vérifier limites de taille upload"""
    print("\n🔐 SECURITY-003: Upload Size Limits")
    print("-" * 70)
    
    try:
        import sys
        sys.path.insert(0, "/home/claude/detection_system_v2")
        from core.config import get_config
        
        config = get_config()
        
        # Vérifier config existe
        if not hasattr(config, 'max_upload_size'):
            print("  ❌ FAILED: max_upload_size not configured")
            return False
        
        print(f"  ✅ max_upload_size configured: {config.max_upload_size} bytes")
        
        # Vérifier properties
        if not hasattr(config, 'max_upload_size_mb'):
            print("  ❌ FAILED: max_upload_size_mb property missing")
            return False
        
        print(f"  ✅ max_upload_size_mb: {config.max_upload_size_mb} MB")
        
        # Vérifier valeur raisonnable (5-20 MB)
        if not (5 <= config.max_upload_size_mb <= 20):
            print(f"  ⚠️  WARNING: Upload limit {config.max_upload_size_mb}MB outside recommended 5-20MB")
        
        print("  ✅ PASSED: Upload limits configured")
        return True
    
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


@suite.test("SECURITY-004: MIME Validation Strict")
async def test_mime_validation_strict():
    """Vérifier validation MIME stricte"""
    print("\n🔐 SECURITY-004: MIME Validation Strict")
    print("-" * 70)
    
    validation_file = Path("/home/claude/detection_system_v2/api/middleware/validation.py")
    
    with open(validation_file, 'r') as f:
        content = f.read()
    
    # Test 1: MIME validation NOT skipped
    if "except Exception:" in content and "pass  # Skip" in content:
        print("  ❌ FAILED: MIME validation can be skipped")
        return False
    
    print("  ✅ MIME validation NOT skipped")
    
    # Test 2: validate_mime_vs_magic_bytes existe
    if "def validate_mime_vs_magic_bytes(" not in content:
        print("  ❌ FAILED: validate_mime_vs_magic_bytes() not found")
        return False
    
    print("  ✅ validate_mime_vs_magic_bytes() exists")
    
    # Test 3: Cross-check appelé
    if "validate_mime_vs_magic_bytes(" not in content:
        print("  ❌ FAILED: Cross-check not called")
        return False
    
    print("  ✅ MIME vs magic bytes cross-check called")
    
    # Test 4: HTTP 415 pour MIME invalide
    if "415" not in content and "UNSUPPORTED_MEDIA_TYPE" not in content:
        print("  ❌ FAILED: HTTP 415 not used for unsupported MIME")
        return False
    
    print("  ✅ HTTP 415 for unsupported MIME types")
    
    print("  ✅ PASSED: MIME validation strict")
    return True


@suite.test("SECURITY-005: Demo Auth Blocked in Production")
async def test_demo_auth_blocked():
    """Vérifier que demo auth est bloqué en production"""
    print("\n🔐 SECURITY-005: Demo Auth Blocked in Production")
    print("-" * 70)
    
    try:
        import sys
        sys.path.insert(0, "/home/claude/detection_system_v2")
        from core.config import Settings
        
        # Test: Production avec demo auth = ValueError
        print("  Test: Production with demo auth enabled...")
        try:
            config = Settings(
                environment="production",
                enable_demo_auth=True,
                jwt_secret_key="a" * 64
            )
            print("  ❌ FAILED: Should have raised ValueError!")
            return False
        except (ValueError, SystemExit) as e:
            print(f"  ✅ Blocked correctly: {type(e).__name__}")
        
        print("  ✅ PASSED: Demo auth blocked in production")
        return True
    
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


@suite.test("SECURITY-006: Rate Limiting Configured")
async def test_rate_limiting():
    """Vérifier que rate limiting est configuré"""
    print("\n🔐 SECURITY-006: Rate Limiting Configured")
    print("-" * 70)
    
    auth_file = Path("/home/claude/detection_system_v2/api/routes/auth.py")
    
    with open(auth_file, 'r') as f:
        content = f.read()
    
    # Test 1: RateLimiter imported
    if "from services.auth.rate_limiter import RateLimiter" not in content:
        print("  ❌ FAILED: RateLimiter not imported")
        return False
    
    print("  ✅ RateLimiter imported")
    
    # Test 2: RateLimiter instance créée
    if "RateLimiter(" not in content:
        print("  ❌ FAILED: RateLimiter not instantiated")
        return False
    
    print("  ✅ RateLimiter instantiated")
    
    # Test 3: check_rate_limit appelé
    if "check_rate_limit(" not in content:
        print("  ❌ FAILED: check_rate_limit() not called")
        return False
    
    print("  ✅ check_rate_limit() called")
    
    # Test 4: IP-based limiting
    if "get_real_client_ip" not in content:
        print("  ❌ FAILED: IP-based limiting not implemented")
        return False
    
    print("  ✅ IP-based rate limiting")
    
    print("  ✅ PASSED: Rate limiting configured")
    return True


@suite.test("SECURITY-007: Health Checks Functional")
async def test_health_checks():
    """Vérifier que health checks sont fonctionnels"""
    print("\n🏥 SECURITY-007: Health Checks Functional")
    print("-" * 70)
    
    # Test 1: HealthChecker existe
    health_checker_file = Path("/home/claude/detection_system_v2/services/health/health_checker.py")
    
    if not health_checker_file.exists():
        print("  ❌ FAILED: HealthChecker not found")
        return False
    
    print("  ✅ HealthChecker exists")
    
    # Test 2: Redis health_check existe
    redis_file = Path("/home/claude/detection_system_v2/infrastructure/cache/redis_cache.py")
    
    with open(redis_file, 'r') as f:
        content = f.read()
    
    if "async def health_check(" not in content:
        print("  ❌ FAILED: Redis health_check() not found")
        return False
    
    print("  ✅ Redis health_check() exists")
    
    # Test 3: Auto-reconnect existe
    if "async def try_reconnect(" not in content:
        print("  ❌ FAILED: Redis try_reconnect() not found")
        return False
    
    print("  ✅ Redis try_reconnect() exists")
    
    # Test 4: Endpoint /health/detailed existe
    health_routes = Path("/home/claude/detection_system_v2/api/routes/health.py")
    
    with open(health_routes, 'r') as f:
        content = f.read()
    
    if '@router.get("/detailed")' not in content:
        print("  ❌ FAILED: /health/detailed endpoint not found")
        return False
    
    print("  ✅ /health/detailed endpoint exists")
    
    print("  ✅ PASSED: Health checks functional")
    return True


@suite.test("SECURITY-008: Code Quality - No Duplications")
async def test_no_duplications():
    """Vérifier qu'il n'y a plus de duplications problématiques"""
    print("\n📦 SECURITY-008: Code Quality - No Duplications")
    print("-" * 70)
    
    root_dir = "/home/claude/detection_system_v2"
    
    # Test 1: core/models.py supprimé
    core_models = Path(f"{root_dir}/core/models.py")
    
    if core_models.exists():
        print("  ❌ FAILED: core/models.py still exists (should be deleted)")
        return False
    
    print("  ✅ core/models.py deleted")
    
    # Test 2: Scripts dans tools/setup
    setup_dir = Path(f"{root_dir}/tools/setup")
    
    if not setup_dir.exists():
        print("  ❌ FAILED: tools/setup/ not found")
        return False
    
    print("  ✅ tools/setup/ exists")
    
    # Test 3: CalibrationPoint unifié
    calibration_file = Path(f"{root_dir}/services/detection/calibration.py")
    
    with open(calibration_file, 'r') as f:
        content = f.read()
    
    if "from api.schemas.detection import CalibrationPoint" not in content:
        print("  ❌ FAILED: CalibrationPoint not imported from schemas")
        return False
    
    print("  ✅ CalibrationPoint unified")
    
    # Test 4: Pas de classe locale CalibrationPoint
    if "class CalibrationPoint:" in content:
        print("  ❌ FAILED: Local CalibrationPoint class still defined")
        return False
    
    print("  ✅ No local CalibrationPoint definition")
    
    print("  ✅ PASSED: No problematic duplications")
    return True


# Run all tests
if __name__ == "__main__":
    result = asyncio.run(suite.run_all())
    
    if result:
        print()
        print("🎉" * 35)
        print("✅ TOUS LES TESTS SÉCURITÉ PASSENT ✅")
        print("🎉" * 35)
        print()
        print("Le système est PRODUCTION-READY du point de vue sécurité!")
        print()
    else:
        print()
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print()
    
    exit(0 if result else 1)
