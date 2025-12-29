"""
Fuel level detection using computer vision

Implements multiple detection methods:
- Hough Transform (line detection)
- K-Means Clustering (color-based)
- Edge Detection + Analysis
- Ensemble method (combines all)

Features:
- Preprocessing pipeline integration
- Calibration support
- Result validation
- Performance optimization
"""
import time
import numpy as np
from typing import Tuple, Optional, List, Dict
import cv2

from services.detection.image_processor import ImageProcessor
from services.detection.calibration import Calibration, create_default_calibration
from services.detection.validator import DetectionResult, ResultValidator


class FuelLevelDetector:
    """
    Fuel level detector using multiple CV methods
    
    Methods available:
    - hough: Hough Transform line detection
    - clustering: K-Means color clustering
    - edge: Edge detection + horizontal analysis
    - ensemble: Combines all methods
    
    Features:
    - Preprocessing integration
    - Calibration support
    - Confidence scoring
    - Performance optimization
    """
    
    def __init__(
        self,
        calibration: Optional[Calibration] = None,
        use_preprocessing: bool = True,
        default_method: str = "ensemble"
    ):
        """
        Initialize detector
        
        Args:
            calibration: Calibration object (creates default if None)
            use_preprocessing: Apply preprocessing pipeline
            default_method: Default detection method
        
        Example:
            >>> detector = FuelLevelDetector(
            ...     calibration=my_calibration,
            ...     default_method="ensemble"
            ... )
        """
        self.calibration = calibration
        self.use_preprocessing = use_preprocessing
        self.default_method = default_method
        
        # Initialize components
        self.preprocessor = ImageProcessor()
        self.validator: Optional[ResultValidator] = None
        
        # Performance stats
        self.detection_count = 0
        self.total_processing_time = 0.0
    
    def detect(
        self,
        image: np.ndarray,
        method: Optional[str] = None
    ) -> DetectionResult:
        """
        Detect fuel level in image
        
        Args:
            image: Input image (BGR or grayscale)
            method: Detection method (None = use default)
        
        Returns:
            DetectionResult: Detection result with confidence
        
        Example:
            >>> result = detector.detect(image, method="ensemble")
            >>> print(f"Level: {result.niveau_percentage}%")
            >>> print(f"Confidence: {result.confiance}")
        """
        start_time = time.time()
        
        # Use default method if not specified
        if method is None:
            method = self.default_method
        
        # Get image dimensions
        image_height, image_width = image.shape[:2]
        
        # Initialize calibration if needed
        if self.calibration is None:
            self.calibration = create_default_calibration(
                image_height=image_height,
                tank_capacity_ml=1000.0
            )
        
        # Initialize validator if needed
        if self.validator is None:
            self.validator = ResultValidator(image_height=image_height)
        
        # Preprocess image
        if self.use_preprocessing:
            processed, metadata = self.preprocessor.preprocess(image)
        else:
            processed = image
            metadata = {}
        
        # Detect level
        if method == "hough":
            result = self._detect_hough(processed, image_width, image_height)
        elif method == "clustering":
            result = self._detect_clustering(processed, image_width, image_height)
        elif method == "edge":
            result = self._detect_edge(processed, image_width, image_height)
        elif method == "ensemble":
            result = self._detect_ensemble(processed, image_width, image_height)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # milliseconds
        result.temps_traitement_ms = processing_time
        
        # Add metadata
        result.metadata.update({
            "preprocessing": metadata,
            "calibration_used": self.calibration.is_calibrated
        })
        
        # Validate result
        is_valid, errors, confidence = self.validator.validate_result(result)
        result.confiance = confidence
        
        if not is_valid:
            result.metadata["validation_errors"] = errors
        
        # Update stats
        self.detection_count += 1
        self.total_processing_time += processing_time
        
        return result
    
    def _detect_hough(
        self,
        image: np.ndarray,
        image_width: int,
        image_height: int
    ) -> DetectionResult:
        """
        Detect fuel level using Hough Transform
        
        Detects horizontal lines in the image.
        The topmost horizontal line is assumed to be the fuel surface.
        
        Args:
            image: Preprocessed image
            image_width: Image width
            image_height: Image height
        
        Returns:
            DetectionResult: Detection result
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Hough Transform for line detection
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi/180,
            threshold=100,
            minLineLength=int(image_width * 0.3),  # Min 30% of width
            maxLineGap=10
        )
        
        if lines is None or len(lines) == 0:
            # No lines detected - use default middle
            niveau_y = image_height // 2
        else:
            # Filter for mostly horizontal lines (angle < 15 degrees)
            horizontal_lines = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                
                # Calculate angle
                if x2 - x1 != 0:
                    angle = abs(np.arctan((y2 - y1) / (x2 - x1)) * 180 / np.pi)
                else:
                    angle = 90
                
                # Keep horizontal lines (angle < 15 degrees)
                if angle < 15:
                    horizontal_lines.append((y1 + y2) / 2)  # Average Y position
            
            if len(horizontal_lines) > 0:
                # Use topmost line (minimum Y)
                niveau_y = int(min(horizontal_lines))
            else:
                # No horizontal lines - use middle
                niveau_y = image_height // 2
        
        # Convert to percentage
        niveau_percentage = self.calibration.pixel_to_percentage(niveau_y)
        niveau_ml = self.calibration.pixel_to_volume(niveau_y)
        
        return DetectionResult(
            niveau_y=niveau_y,
            niveau_percentage=niveau_percentage,
            niveau_ml=niveau_ml,
            methode_utilisee="hough",
            image_width=image_width,
            image_height=image_height
        )
    
    def _detect_clustering(
        self,
        image: np.ndarray,
        image_width: int,
        image_height: int
    ) -> DetectionResult:
        """
        Detect fuel level using K-Means clustering
        
        Clusters pixels by color, then finds the boundary between
        the fuel (darker) and air (lighter) clusters.
        
        Args:
            image: Preprocessed image
            image_width: Image width
            image_height: Image height
        
        Returns:
            DetectionResult: Detection result
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Flatten image for clustering
        pixels = gray.reshape(-1, 1).astype(np.float32)
        
        # K-Means clustering (k=2: fuel vs air)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        k = 2
        _, labels, centers = cv2.kmeans(
            pixels,
            k,
            None,
            criteria,
            attempts=10,
            flags=cv2.KMEANS_RANDOM_CENTERS
        )
        
        # Reshape labels
        labels = labels.reshape(gray.shape)
        
        # Determine which cluster is fuel (darker = lower center value)
        fuel_label = 0 if centers[0] < centers[1] else 1
        
        # Find boundary between clusters
        # Scan from top to bottom, find first row with significant fuel pixels
        threshold = image_width * 0.3  # At least 30% of width
        
        niveau_y = image_height // 2  # Default
        
        for y in range(image_height):
            row = labels[y, :]
            fuel_pixels = np.sum(row == fuel_label)
            
            if fuel_pixels >= threshold:
                niveau_y = y
                break
        
        # Convert to percentage
        niveau_percentage = self.calibration.pixel_to_percentage(niveau_y)
        niveau_ml = self.calibration.pixel_to_volume(niveau_y)
        
        return DetectionResult(
            niveau_y=niveau_y,
            niveau_percentage=niveau_percentage,
            niveau_ml=niveau_ml,
            methode_utilisee="clustering",
            image_width=image_width,
            image_height=image_height
        )
    
    def _detect_edge(
        self,
        image: np.ndarray,
        image_width: int,
        image_height: int
    ) -> DetectionResult:
        """
        Detect fuel level using edge detection + horizontal analysis
        
        Detects edges, then analyzes horizontal edge density
        to find the fuel surface.
        
        Args:
            image: Preprocessed image
            image_width: Image width
            image_height: Image height
        
        Returns:
            DetectionResult: Detection result
        """
        # Detect edges
        edges = self.preprocessor.detect_edges(image, method="canny")
        
        # Calculate horizontal edge density for each row
        row_densities = np.sum(edges > 0, axis=1) / image_width
        
        # Smooth densities
        kernel_size = 11
        kernel = np.ones(kernel_size) / kernel_size
        smoothed = np.convolve(row_densities, kernel, mode='same')
        
        # Find peak density in upper half (likely fuel surface)
        upper_half = image_height // 2
        peak_idx = np.argmax(smoothed[:upper_half])
        
        niveau_y = peak_idx if peak_idx > 0 else image_height // 2
        
        # Convert to percentage
        niveau_percentage = self.calibration.pixel_to_percentage(niveau_y)
        niveau_ml = self.calibration.pixel_to_volume(niveau_y)
        
        return DetectionResult(
            niveau_y=niveau_y,
            niveau_percentage=niveau_percentage,
            niveau_ml=niveau_ml,
            methode_utilisee="edge",
            image_width=image_width,
            image_height=image_height
        )
    
    def _detect_ensemble(
        self,
        image: np.ndarray,
        image_width: int,
        image_height: int
    ) -> DetectionResult:
        """
        Detect fuel level using ensemble of all methods
        
        Combines results from Hough, Clustering, and Edge methods.
        Uses weighted average based on individual confidences.
        
        Args:
            image: Preprocessed image
            image_width: Image width
            image_height: Image height
        
        Returns:
            DetectionResult: Combined detection result
        """
        # Run all methods
        hough_result = self._detect_hough(image, image_width, image_height)
        clustering_result = self._detect_clustering(image, image_width, image_height)
        edge_result = self._detect_edge(image, image_width, image_height)
        
        # Collect all results
        all_results = [hough_result, clustering_result, edge_result]
        
        # Calculate weights (simple average for now)
        weights = [1.0, 1.0, 1.0]
        total_weight = sum(weights)
        
        # Weighted average of positions
        weighted_y = sum(r.niveau_y * w for r, w in zip(all_results, weights)) / total_weight
        niveau_y = int(weighted_y)
        
        # Convert to percentage
        niveau_percentage = self.calibration.pixel_to_percentage(niveau_y)
        niveau_ml = self.calibration.pixel_to_volume(niveau_y)
        
        # Create ensemble result
        result = DetectionResult(
            niveau_y=niveau_y,
            niveau_percentage=niveau_percentage,
            niveau_ml=niveau_ml,
            methode_utilisee="ensemble",
            image_width=image_width,
            image_height=image_height,
            metadata={
                "methods": {
                    "hough": hough_result.niveau_y,
                    "clustering": clustering_result.niveau_y,
                    "edge": edge_result.niveau_y
                },
                "std_deviation": np.std([r.niveau_y for r in all_results])
            }
        )
        
        return result
    
    def get_stats(self) -> dict:
        """
        Get detector statistics
        
        Returns:
            dict: Performance statistics
        
        Example:
            >>> stats = detector.get_stats()
            >>> print(f"Avg time: {stats['avg_processing_time_ms']}ms")
        """
        avg_time = 0.0
        if self.detection_count > 0:
            avg_time = self.total_processing_time / self.detection_count
        
        stats = {
            "detection_count": self.detection_count,
            "total_processing_time_ms": round(self.total_processing_time, 2),
            "avg_processing_time_ms": round(avg_time, 2),
            "calibrated": self.calibration is not None and self.calibration.is_calibrated,
            "preprocessing_enabled": self.use_preprocessing
        }
        
        # Add validator stats if available
        if self.validator:
            stats["validator"] = self.validator.get_statistics()
        
        return stats
