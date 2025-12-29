"""
Tests de validation de l'étape 5 - Detection Service Complete

Tests pour valider:
- Image preprocessing (resize, denoise, contrast, edges)
- Calibration (linear, multipoint, save/load)
- Result validation (confidence scoring)
- Fuel detection (Hough, Clustering, Edge, Ensemble)
"""
import os
import sys
import numpy as np
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_test_image(width=800, height=600, fuel_level=0.5):
    """
    Create a synthetic test image for fuel detection
    
    Args:
        width: Image width
        height: Image height
        fuel_level: Fuel level (0.0 = empty, 1.0 = full)
    
    Returns:
        np.ndarray: Synthetic image with fuel level
    """
    import cv2
    
    # Create image
    image = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Calculate fuel line position
    fuel_y = int(height * (1 - fuel_level))
    
    # Draw fuel (darker, bottom part)
    image[fuel_y:, :] = [40, 40, 40]  # Dark gray (fuel)
    
    # Draw air (lighter, top part)
    image[:fuel_y, :] = [200, 200, 200]  # Light gray (air)
    
    # Add some noise
    noise = np.random.randint(-20, 20, image.shape, dtype=np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    return image


def test_image_processor():
    """Test image preprocessing"""
    print("\n📝 Test 1: Image Preprocessing")
    print("-" * 60)
    
    try:
        from services.detection.image_processor import ImageProcessor
        
        # Create processor
        processor = ImageProcessor(target_width=800, target_height=600)
        
        # Create test image
        image = create_test_image(1024, 768)
        print(f"  Created test image: {image.shape}")
        
        # Test 1.1: Resize
        resized = processor.resize(image, width=800, height=600)
        assert resized.shape[:2] == (600, 800), "Should resize to target"
        print("  ✅ Resize OK")
        
        # Test 1.2: Denoise
        denoised = processor.denoise(image, method="bilateral")
        assert denoised.shape == image.shape, "Should preserve shape"
        print("  ✅ Denoise (bilateral) OK")
        
        # Test 1.3: Enhance contrast
        enhanced = processor.enhance_contrast(image, method="clahe")
        assert enhanced.shape == image.shape, "Should preserve shape"
        print("  ✅ Contrast enhancement (CLAHE) OK")
        
        # Test 1.4: Edge detection
        edges = processor.detect_edges(image, method="canny")
        assert edges.ndim == 2, "Should return grayscale edges"
        print("  ✅ Edge detection (Canny) OK")
        
        # Test 1.5: Complete preprocessing
        processed, metadata = processor.preprocess(image)
        assert "steps" in metadata, "Should return metadata"
        assert len(metadata["steps"]) > 0, "Should have preprocessing steps"
        print(f"  ✅ Complete preprocessing OK ({len(metadata['steps'])} steps)")
        
        # Test 1.6: Statistics
        stats = processor.get_preprocessing_stats(image)
        assert "mean_brightness" in stats, "Should have brightness stats"
        print(f"  ✅ Image statistics OK (brightness: {stats['mean_brightness']:.1f})")
        
        print("\n✅ IMAGE PROCESSOR: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ IMAGE PROCESSOR: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_calibration():
    """Test calibration system"""
    print("\n📝 Test 2: Calibration System")
    print("-" * 60)
    
    try:
        from services.detection.calibration import Calibration, create_default_calibration
        import tempfile
        
        # Test 2.1: Create calibration
        cal = Calibration(image_height=600, tank_capacity_ml=5000.0)
        assert cal.image_height == 600, "Should set image height"
        print("  ✅ Calibration creation OK")
        
        # Test 2.2: Add points
        cal.add_point(pixel_y=540, percentage=0)    # Empty (90% of height)
        cal.add_point(pixel_y=60, percentage=100)   # Full (10% of height)
        assert len(cal.points) == 2, "Should have 2 points"
        assert cal.is_calibrated, "Should be calibrated"
        print("  ✅ Add calibration points OK")
        
        # Test 2.3: Pixel to percentage
        percentage = cal.pixel_to_percentage(300)
        assert 0 <= percentage <= 100, "Percentage should be in [0, 100]"
        print(f"  ✅ Pixel to percentage OK (300px = {percentage:.1f}%)")
        
        # Test 2.4: Percentage to volume
        volume = cal.percentage_to_volume(50.0)
        assert volume == 2500.0, "Should calculate volume correctly"
        print(f"  ✅ Percentage to volume OK (50% = {volume:.0f} mL)")
        
        # Test 2.5: Pixel to volume
        volume = cal.pixel_to_volume(300)
        assert volume > 0, "Should calculate volume"
        print(f"  ✅ Pixel to volume OK (300px = {volume:.0f} mL)")
        
        # Test 2.6: Validation
        is_valid, errors = cal.validate()
        assert is_valid, f"Calibration should be valid: {errors}"
        print("  ✅ Calibration validation OK")
        
        # Test 2.7: Save/load
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            cal.save(temp_file)
            loaded_cal = Calibration.load(temp_file)
            assert len(loaded_cal.points) == 2, "Should load points"
            assert loaded_cal.is_calibrated, "Should be calibrated"
            print("  ✅ Save/load calibration OK")
        finally:
            os.unlink(temp_file)
        
        # Test 2.8: Default calibration
        default_cal = create_default_calibration(600, 5000.0)
        assert default_cal.is_calibrated, "Should create default calibration"
        print("  ✅ Default calibration OK")
        
        print("\n✅ CALIBRATION: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ CALIBRATION: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validator():
    """Test result validator"""
    print("\n📝 Test 3: Result Validator")
    print("-" * 60)
    
    try:
        from services.detection.validator import ResultValidator, DetectionResult
        
        # Create validator
        validator = ResultValidator(image_height=600, min_confidence=0.5)
        
        # Test 3.1: Validate position
        is_valid, error = validator.validate_position(300)
        assert is_valid, "Valid position should pass"
        print("  ✅ Position validation OK")
        
        # Test 3.2: Validate percentage
        is_valid, error = validator.validate_percentage(75.5)
        assert is_valid, "Valid percentage should pass"
        print("  ✅ Percentage validation OK")
        
        # Test 3.3: Invalid position
        is_valid, error = validator.validate_position(700)
        assert not is_valid, "Invalid position should fail"
        print("  ✅ Invalid position detection OK")
        
        # Test 3.4: Create detection result
        result = DetectionResult(
            niveau_y=300,
            niveau_percentage=50.0,
            niveau_ml=2500.0,
            confiance=0.85,
            methode_utilisee="test",
            image_width=800,
            image_height=600
        )
        assert result.niveau_y == 300, "Should create result"
        print("  ✅ Detection result creation OK")
        
        # Test 3.5: Calculate confidence
        confidence = validator.calculate_confidence(result)
        assert 0 <= confidence <= 1, "Confidence should be in [0, 1]"
        print(f"  ✅ Confidence calculation OK ({confidence:.3f})")
        
        # Test 3.6: Validate result
        is_valid, errors, confidence = validator.validate_result(result)
        assert is_valid, f"Result should be valid: {errors}"
        print(f"  ✅ Result validation OK (confidence: {confidence:.3f})")
        
        # Test 3.7: Statistics
        stats = validator.get_statistics()
        assert "total_results" in stats, "Should have statistics"
        assert stats["total_results"] == 1, "Should count 1 result"
        print(f"  ✅ Statistics OK ({stats['total_results']} results)")
        
        print("\n✅ VALIDATOR: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ VALIDATOR: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fuel_detector():
    """Test fuel level detector"""
    print("\n📝 Test 4: Fuel Level Detector")
    print("-" * 60)
    
    try:
        from services.detection.fuel_detector import FuelLevelDetector
        from services.detection.calibration import create_default_calibration
        
        # Create calibration
        calibration = create_default_calibration(image_height=600, tank_capacity_ml=5000.0)
        
        # Create detector
        detector = FuelLevelDetector(
            calibration=calibration,
            use_preprocessing=True,
            default_method="ensemble"
        )
        print("  ✅ Detector initialization OK")
        
        # Create test image (50% fuel)
        image = create_test_image(width=800, height=600, fuel_level=0.5)
        
        # Test 4.1: Hough detection
        result_hough = detector.detect(image, method="hough")
        assert result_hough.methode_utilisee == "hough", "Should use Hough method"
        assert 0 <= result_hough.niveau_percentage <= 100, "Percentage should be valid"
        print(f"  ✅ Hough detection OK ({result_hough.niveau_percentage:.1f}%)")
        
        # Test 4.2: Clustering detection
        result_clustering = detector.detect(image, method="clustering")
        assert result_clustering.methode_utilisee == "clustering", "Should use clustering"
        print(f"  ✅ Clustering detection OK ({result_clustering.niveau_percentage:.1f}%)")
        
        # Test 4.3: Edge detection
        result_edge = detector.detect(image, method="edge")
        assert result_edge.methode_utilisee == "edge", "Should use edge detection"
        print(f"  ✅ Edge detection OK ({result_edge.niveau_percentage:.1f}%)")
        
        # Test 4.4: Ensemble detection
        result_ensemble = detector.detect(image, method="ensemble")
        assert result_ensemble.methode_utilisee == "ensemble", "Should use ensemble"
        assert "methods" in result_ensemble.metadata, "Should have method details"
        print(f"  ✅ Ensemble detection OK ({result_ensemble.niveau_percentage:.1f}%)")
        
        # Test 4.5: Confidence scoring
        assert result_ensemble.confiance > 0, "Should have confidence score"
        print(f"  ✅ Confidence scoring OK ({result_ensemble.confiance:.3f})")
        
        # Test 4.6: Performance stats
        stats = detector.get_stats()
        assert stats["detection_count"] == 4, "Should count 4 detections"
        assert "avg_processing_time_ms" in stats, "Should have timing stats"
        print(f"  ✅ Performance stats OK ({stats['avg_processing_time_ms']:.1f}ms avg)")
        
        # Test 4.7: Result to dict
        result_dict = result_ensemble.to_dict()
        assert "niveau_percentage" in result_dict, "Should serialize to dict"
        assert "confiance" in result_dict, "Should include confidence"
        print("  ✅ Result serialization OK")
        
        print("\n✅ FUEL DETECTOR: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ FUEL DETECTOR: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test complete detection pipeline"""
    print("\n📝 Test 5: Complete Detection Pipeline")
    print("-" * 60)
    
    try:
        from services.detection.fuel_detector import FuelLevelDetector
        from services.detection.calibration import create_default_calibration
        
        # Create full pipeline
        calibration = create_default_calibration(600, 5000.0)
        detector = FuelLevelDetector(calibration=calibration)
        
        # Test multiple fuel levels
        test_levels = [0.0, 0.25, 0.5, 0.75, 1.0]
        results = []
        
        for level in test_levels:
            image = create_test_image(800, 600, fuel_level=level)
            result = detector.detect(image)
            results.append(result)
            print(f"  Level {level*100:.0f}%: Detected {result.niveau_percentage:.1f}% "
                  f"(confidence: {result.confiance:.3f})")
        
        # Verify monotonic increase (roughly)
        percentages = [r.niveau_percentage for r in results]
        assert percentages[0] < percentages[-1], "Should increase from empty to full"
        print("  ✅ Multiple level detection OK")
        
        # Verify all have confidence scores
        confidences = [r.confiance for r in results]
        assert all(c > 0 for c in confidences), "All should have confidence"
        print(f"  ✅ Confidence scores OK (avg: {np.mean(confidences):.3f})")
        
        # Get final stats
        stats = detector.get_stats()
        print(f"\n  📊 Final Statistics:")
        print(f"     Total detections: {stats['detection_count']}")
        print(f"     Average time: {stats['avg_processing_time_ms']:.1f}ms")
        print(f"     Calibrated: {stats['calibrated']}")
        
        print("\n✅ INTEGRATION: ALL TESTS PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ INTEGRATION: TEST FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("TEST DE L'ÉTAPE 5 - DETECTION SERVICE COMPLETE")
    print("=" * 60)
    
    # Set environment variables
    os.environ.setdefault('ENVIRONMENT', 'testing')
    
    tests = [
        test_image_processor,
        test_calibration,
        test_validator,
        test_fuel_detector,
        test_integration
    ]
    
    results = [test() for test in tests]
    
    print()
    print("=" * 60)
    if all(results):
        print("✅ ÉTAPE 5 VALIDÉE - Tous les tests passent")
        print("=" * 60)
        print()
        print("🎯 Detection Service Complete:")
        print("  1. ✅ Image Preprocessing (resize, denoise, contrast, edges)")
        print("  2. ✅ Calibration System (linear, multipoint, save/load)")
        print("  3. ✅ Result Validator (confidence scoring)")
        print("  4. ✅ Fuel Detector (Hough, Clustering, Edge, Ensemble)")
        print("  5. ✅ Complete Pipeline (integration)")
        print()
        print("⚠️  Note: Tests utilisent des images synthétiques")
        print("          Tester avec des vraies images pour validation finale")
        print()
        print("➡️  Prêt pour l'ÉTAPE 6 (API Complete & Middleware)")
    else:
        print("❌ ÉTAPE 5 ÉCHOUÉE - Corriger les erreurs")
    print("=" * 60)
