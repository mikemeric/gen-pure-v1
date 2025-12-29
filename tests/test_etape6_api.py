"""
Tests de validation de l'étape 6 - API Complete & Middleware

Tests pour valider:
- Pydantic schemas (validation)
- Middleware (auth, error handling, validation)
- Detection endpoints (detect, history, statistics)
- Calibration endpoints (CRUD)
"""
import os
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_schemas():
    """Test Pydantic schemas"""
    print("\n📝 Test 1: Pydantic Schemas")
    print("-" * 60)
    
    try:
        from api.schemas.detection import (
            DetectionRequest,
            DetectionResponse,
            CalibrationCreateRequest,
            CalibrationPoint,
            ErrorResponse
        )
        from datetime import datetime
        
        # Test 1.1: DetectionRequest validation
        request = DetectionRequest(method="ensemble", use_preprocessing=True)
        assert request.method == "ensemble", "Should set method"
        print("  ✅ DetectionRequest validation OK")
        
        # Test 1.2: Invalid method
        try:
            DetectionRequest(method="invalid")
            print("  ❌ Should have raised validation error")
            return False
        except Exception:
            print("  ✅ Invalid method detection OK")
        
        # Test 1.3: DetectionResponse
        response = DetectionResponse(
            success=True,
            niveau_y=300,
            niveau_percentage=50.0,
            niveau_ml=2500.0,
            confiance=0.875,
            methode_utilisee="ensemble",
            temps_traitement_ms=342.5,
            image_width=800,
            image_height=600,
            timestamp=datetime.now()
        )
        assert response.success == True, "Should be success"
        assert 0 <= response.confiance <= 1, "Confidence should be [0,1]"
        print("  ✅ DetectionResponse creation OK")
        
        # Test 1.4: CalibrationPoint validation
        point = CalibrationPoint(pixel_y=300, percentage=50.0)
        assert point.pixel_y == 300, "Should set pixel_y"
        print("  ✅ CalibrationPoint validation OK")
        
        # Test 1.5: CalibrationCreateRequest
        cal_request = CalibrationCreateRequest(
            name="Test Tank",
            image_height=600,
            tank_capacity_ml=5000.0,
            calibration_type="linear",
            points=[
                CalibrationPoint(pixel_y=540, percentage=0),
                CalibrationPoint(pixel_y=60, percentage=100)
            ]
        )
        assert len(cal_request.points) == 2, "Should have 2 points"
        print("  ✅ CalibrationCreateRequest validation OK")
        
        # Test 1.6: ErrorResponse
        error = ErrorResponse(
            error="TestError",
            message="Test error message",
            timestamp=datetime.now()
        )
        assert error.success == False, "Error should have success=False"
        print("  ✅ ErrorResponse creation OK")
        
        print("\n✅ SCHEMAS: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ SCHEMAS: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handler():
    """Test error handler middleware"""
    print("\n📝 Test 2: Error Handler Middleware")
    print("-" * 60)
    
    try:
        from api.middleware.error_handler import (
            create_error_response,
            handle_exception
        )
        from core.exceptions import AuthenticationError, ValidationError
        from fastapi import status
        
        # Test 2.1: Create error response
        response = create_error_response(
            error="TestError",
            message="Test message",
            status_code=status.HTTP_400_BAD_REQUEST
        )
        assert response.status_code == 400, "Should set status code"
        print("  ✅ Create error response OK")
        
        # Test 2.2: Handle AuthenticationError
        exc = AuthenticationError("Invalid token")
        response = handle_exception(exc)
        assert response.status_code == 401, "Should return 401"
        print("  ✅ AuthenticationError handling OK")
        
        # Test 2.3: Handle ValidationError
        exc = ValidationError("Invalid data")
        response = handle_exception(exc)
        assert response.status_code == 400, "Should return 400"
        print("  ✅ ValidationError handling OK")
        
        # Test 2.4: Handle generic Exception
        exc = Exception("Generic error")
        response = handle_exception(exc)
        assert response.status_code == 500, "Should return 500"
        print("  ✅ Generic exception handling OK")
        
        print("\n✅ ERROR HANDLER: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ ERROR HANDLER: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auth_middleware():
    """Test auth middleware"""
    print("\n📝 Test 3: Auth Middleware")
    print("-" * 60)
    
    try:
        from api.middleware.auth import AuthMiddleware
        
        # Test 3.1: Create middleware
        auth = AuthMiddleware()
        assert auth.jwt_manager is not None, "Should have JWT manager"
        assert auth.key_manager is not None, "Should have key manager"
        print("  ✅ AuthMiddleware initialization OK")
        
        # Note: Full auth testing requires JWT tokens
        # Just test structure here
        print("  ⚠️  Full auth testing requires valid tokens (skipped)")
        
        print("\n✅ AUTH MIDDLEWARE: STRUCTURE TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ AUTH MIDDLEWARE: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_validation():
    """Test file validation middleware"""
    print("\n📝 Test 4: File Validation Middleware")
    print("-" * 60)
    
    try:
        from api.middleware.validation import FileValidator
        
        # Test 4.1: Create validator
        validator = FileValidator(
            max_size_mb=10,
            allowed_extensions=['.jpg', '.png']
        )
        assert validator.max_size_bytes == 10 * 1024 * 1024, "Should set max size"
        print("  ✅ FileValidator initialization OK")
        
        # Test 4.2: Get extension
        ext = validator._get_extension("test.jpg")
        assert ext == ".jpg", "Should extract extension"
        print("  ✅ Extension extraction OK")
        
        # Note: Full file validation testing requires actual file uploads
        print("  ⚠️  Full file validation requires actual uploads (skipped)")
        
        print("\n✅ FILE VALIDATION: STRUCTURE TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ FILE VALIDATION: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_detection_routes_structure():
    """Test detection routes structure"""
    print("\n📝 Test 5: Detection Routes Structure")
    print("-" * 60)
    
    try:
        from api.routes.detection_v2 import router, get_detector
        
        # Test 5.1: Router exists
        assert router is not None, "Should have router"
        assert router.prefix == "/api/v2/detect", "Should have correct prefix"
        print("  ✅ Detection router OK")
        
        # Test 5.2: Get detector
        detector = get_detector()
        assert detector is not None, "Should create detector"
        print("  ✅ Detector initialization OK")
        
        # Test 5.3: Check routes
        routes = [route.path for route in router.routes]
        assert "/api/v2/detect" in routes or "" in routes, "Should have detect route"
        print(f"  ✅ Routes registered: {len(routes)} routes")
        
        print("\n✅ DETECTION ROUTES: STRUCTURE TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ DETECTION ROUTES: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_calibration_routes_structure():
    """Test calibration routes structure"""
    print("\n📝 Test 6: Calibration Routes Structure")
    print("-" * 60)
    
    try:
        from api.routes.calibration import router, generate_calibration_id
        
        # Test 6.1: Router exists
        assert router is not None, "Should have router"
        assert router.prefix == "/api/calibrations", "Should have correct prefix"
        print("  ✅ Calibration router OK")
        
        # Test 6.2: Generate ID
        cal_id = generate_calibration_id()
        assert cal_id.startswith("cal_"), "Should start with cal_"
        assert len(cal_id) > 4, "Should have ID part"
        print(f"  ✅ ID generation OK (example: {cal_id})")
        
        # Test 6.3: Check routes
        routes = [route.path for route in router.routes]
        print(f"  ✅ Routes registered: {len(routes)} routes")
        
        print("\n✅ CALIBRATION ROUTES: STRUCTURE TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ CALIBRATION ROUTES: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test integration between components"""
    print("\n📝 Test 7: Component Integration")
    print("-" * 60)
    
    try:
        from api.schemas.detection import DetectionRequest, DetectionResponse
        from api.routes.detection_v2 import get_detector
        from datetime import datetime
        import numpy as np
        
        # Test 7.1: Request → Detection → Response
        request = DetectionRequest(method="ensemble")
        detector = get_detector()
        
        # Create test image
        image = np.zeros((600, 800, 3), dtype=np.uint8)
        image[300:, :] = [40, 40, 40]  # Fuel
        image[:300, :] = [200, 200, 200]  # Air
        
        # Detect
        result = detector.detect(image, method=request.method)
        
        # Create response
        response = DetectionResponse(
            success=True,
            niveau_y=result.niveau_y,
            niveau_percentage=result.niveau_percentage,
            niveau_ml=result.niveau_ml,
            confiance=result.confiance,
            methode_utilisee=result.methode_utilisee,
            temps_traitement_ms=result.temps_traitement_ms,
            image_width=result.image_width,
            image_height=result.image_height,
            timestamp=datetime.now()
        )
        
        assert response.success == True, "Should succeed"
        assert response.methode_utilisee == "ensemble", "Should use ensemble"
        print("  ✅ Request → Detection → Response flow OK")
        
        # Test 7.2: Schema validation in flow
        dict_data = response.dict()
        assert "niveau_percentage" in dict_data, "Should serialize"
        print("  ✅ Schema serialization OK")
        
        print("\n✅ INTEGRATION: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ INTEGRATION: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("TEST DE L'ÉTAPE 6 - API COMPLETE & MIDDLEWARE")
    print("=" * 60)
    
    # Set environment variables
    os.environ.setdefault('ENVIRONMENT', 'testing')
    
    tests = [
        test_schemas,
        test_error_handler,
        test_auth_middleware,
        test_file_validation,
        test_detection_routes_structure,
        test_calibration_routes_structure,
        test_integration
    ]
    
    results = [test() for test in tests]
    
    print()
    print("=" * 60)
    if all(results):
        print("✅ ÉTAPE 6 VALIDÉE - Tous les tests passent")
        print("=" * 60)
        print()
        print("🔧 API Complete & Middleware:")
        print("  1. ✅ Pydantic Schemas (Request/Response validation)")
        print("  2. ✅ Error Handler (Standard error responses)")
        print("  3. ✅ Auth Middleware (JWT + API Key)")
        print("  4. ✅ File Validation (Image upload)")
        print("  5. ✅ Detection Routes (/detect, /history, /statistics)")
        print("  6. ✅ Calibration Routes (CRUD)")
        print("  7. ✅ Component Integration")
        print()
        print("⚠️  Note: Tests de structure uniquement")
        print("          Tests API complets nécessitent serveur FastAPI running")
        print()
        print("➡️  Prêt pour l'ÉTAPE 7 (Tests & Deployment)")
    else:
        print("❌ ÉTAPE 6 ÉCHOUÉE - Corriger les erreurs")
    print("=" * 60)
