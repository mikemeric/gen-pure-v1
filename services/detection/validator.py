"""
Result validation for fuel level detection

Provides validation and confidence scoring:
- Sanity checks on detected level
- Confidence score calculation
- Multiple detection method comparison
- Historical consistency checking
"""
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta


class DetectionResult:
    """
    Detection result with metadata
    
    Attributes:
        niveau_y: Y position in pixels
        niveau_percentage: Fuel level percentage
        niveau_ml: Volume in milliliters
        confiance: Confidence score (0-1)
        methode_utilisee: Detection method used
        image_width: Image width
        image_height: Image height
        temps_traitement_ms: Processing time
        metadata: Additional metadata
    """
    
    def __init__(
        self,
        niveau_y: int,
        niveau_percentage: float,
        niveau_ml: Optional[float] = None,
        confiance: float = 0.0,
        methode_utilisee: str = "unknown",
        image_width: int = 0,
        image_height: int = 0,
        temps_traitement_ms: float = 0.0,
        metadata: Optional[dict] = None
    ):
        self.niveau_y = niveau_y
        self.niveau_percentage = niveau_percentage
        self.niveau_ml = niveau_ml
        self.confiance = confiance
        self.methode_utilisee = methode_utilisee
        self.image_width = image_width
        self.image_height = image_height
        self.temps_traitement_ms = temps_traitement_ms
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()  # UTC for consistency with DB models
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "niveau_y": self.niveau_y,
            "niveau_percentage": round(self.niveau_percentage, 2),
            "niveau_ml": round(self.niveau_ml, 2) if self.niveau_ml else None,
            "confiance": round(self.confiance, 3),
            "methode_utilisee": self.methode_utilisee,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "temps_traitement_ms": round(self.temps_traitement_ms, 2),
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class ResultValidator:
    """
    Validator for detection results
    
    Features:
    - Sanity checks (position, percentage range)
    - Confidence score calculation
    - Multiple method comparison
    - Historical consistency
    """
    
    def __init__(
        self,
        image_height: int,
        min_confidence: float = 0.5,
        max_change_per_minute: float = 20.0
    ):
        """
        Initialize validator
        
        Args:
            image_height: Image height in pixels
            min_confidence: Minimum acceptable confidence
            max_change_per_minute: Max level change per minute (%)
        
        Example:
            >>> validator = ResultValidator(
            ...     image_height=600,
            ...     min_confidence=0.5
            ... )
        """
        self.image_height = image_height
        self.min_confidence = min_confidence
        self.max_change_per_minute = max_change_per_minute
        
        # Historical results
        self.history: List[DetectionResult] = []
        self.max_history = 100
    
    def validate_position(self, pixel_y: int) -> Tuple[bool, str]:
        """
        Validate pixel position
        
        Args:
            pixel_y: Y position in pixels
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        
        Example:
            >>> is_valid, error = validator.validate_position(300)
        """
        if pixel_y < 0:
            return False, f"Position {pixel_y} is negative"
        
        if pixel_y > self.image_height:
            return False, f"Position {pixel_y} exceeds image height {self.image_height}"
        
        return True, ""
    
    def validate_percentage(self, percentage: float) -> Tuple[bool, str]:
        """
        Validate percentage value
        
        Args:
            percentage: Fuel level percentage
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        
        Example:
            >>> is_valid, error = validator.validate_percentage(75.5)
        """
        if percentage < 0:
            return False, f"Percentage {percentage} is negative"
        
        if percentage > 100:
            return False, f"Percentage {percentage} exceeds 100"
        
        return True, ""
    
    def calculate_confidence(
        self,
        result: DetectionResult,
        additional_methods: Optional[List[DetectionResult]] = None
    ) -> float:
        """
        Calculate confidence score for detection result
        
        Confidence factors:
        - Position validity (0.2)
        - Percentage validity (0.2)
        - Historical consistency (0.3)
        - Method agreement (0.3 if multiple methods)
        
        Args:
            result: Detection result
            additional_methods: Results from other methods
        
        Returns:
            float: Confidence score (0-1)
        
        Example:
            >>> confidence = validator.calculate_confidence(result)
        """
        confidence = 0.0
        
        # Factor 1: Position validity (0.2)
        pos_valid, _ = self.validate_position(result.niveau_y)
        if pos_valid:
            confidence += 0.2
        
        # Factor 2: Percentage validity (0.2)
        pct_valid, _ = self.validate_percentage(result.niveau_percentage)
        if pct_valid:
            confidence += 0.2
        
        # Factor 3: Historical consistency (0.3)
        if len(self.history) > 0:
            consistency_score = self._check_historical_consistency(result)
            confidence += 0.3 * consistency_score
        else:
            # No history, give benefit of doubt
            confidence += 0.15
        
        # Factor 4: Method agreement (0.3)
        if additional_methods and len(additional_methods) > 0:
            agreement_score = self._calculate_method_agreement(result, additional_methods)
            confidence += 0.3 * agreement_score
        else:
            # Single method, partial credit
            confidence += 0.15
        
        return min(1.0, max(0.0, confidence))
    
    def _check_historical_consistency(self, result: DetectionResult) -> float:
        """
        Check consistency with historical results
        
        Args:
            result: Current detection result
        
        Returns:
            float: Consistency score (0-1)
        """
        if len(self.history) == 0:
            return 1.0
        
        # Get most recent result
        last_result = self.history[-1]
        
        # Calculate time difference
        time_diff = (result.timestamp - last_result.timestamp).total_seconds() / 60.0  # minutes
        
        if time_diff == 0:
            time_diff = 0.1  # Avoid division by zero
        
        # Calculate percentage change
        percentage_change = abs(result.niveau_percentage - last_result.niveau_percentage)
        
        # Expected max change based on time
        expected_max_change = self.max_change_per_minute * time_diff
        
        # Score based on how reasonable the change is
        if percentage_change <= expected_max_change:
            # Reasonable change
            score = 1.0
        else:
            # Excessive change
            excess = percentage_change - expected_max_change
            score = max(0.0, 1.0 - (excess / 50.0))  # Penalty for excess change
        
        return score
    
    def _calculate_method_agreement(
        self,
        primary_result: DetectionResult,
        other_results: List[DetectionResult]
    ) -> float:
        """
        Calculate agreement between multiple detection methods
        
        Args:
            primary_result: Primary detection result
            other_results: Results from other methods
        
        Returns:
            float: Agreement score (0-1)
        """
        if len(other_results) == 0:
            return 0.5
        
        # Calculate average percentage from all results
        all_percentages = [primary_result.niveau_percentage] + \
                         [r.niveau_percentage for r in other_results]
        
        mean_percentage = np.mean(all_percentages)
        std_percentage = np.std(all_percentages)
        
        # Agreement score based on standard deviation
        # Low std = high agreement
        if std_percentage < 5.0:
            score = 1.0
        elif std_percentage < 10.0:
            score = 0.8
        elif std_percentage < 15.0:
            score = 0.6
        elif std_percentage < 20.0:
            score = 0.4
        else:
            score = 0.2
        
        return score
    
    def validate_result(
        self,
        result: DetectionResult,
        additional_methods: Optional[List[DetectionResult]] = None
    ) -> Tuple[bool, List[str], float]:
        """
        Validate detection result
        
        Args:
            result: Detection result to validate
            additional_methods: Results from other methods
        
        Returns:
            Tuple[bool, List[str], float]: (is_valid, errors, confidence)
        
        Example:
            >>> is_valid, errors, confidence = validator.validate_result(result)
            >>> if is_valid:
            ...     print(f"Valid with confidence {confidence}")
        """
        errors = []
        
        # Validate position
        pos_valid, pos_error = self.validate_position(result.niveau_y)
        if not pos_valid:
            errors.append(pos_error)
        
        # Validate percentage
        pct_valid, pct_error = self.validate_percentage(result.niveau_percentage)
        if not pct_valid:
            errors.append(pct_error)
        
        # Calculate confidence
        confidence = self.calculate_confidence(result, additional_methods)
        result.confiance = confidence
        
        # Check minimum confidence
        if confidence < self.min_confidence:
            errors.append(f"Confidence {confidence:.3f} below minimum {self.min_confidence}")
        
        # Add to history if valid
        is_valid = len(errors) == 0
        if is_valid:
            self._add_to_history(result)
        
        return is_valid, errors, confidence
    
    def _add_to_history(self, result: DetectionResult):
        """Add result to history"""
        self.history.append(result)
        
        # Limit history size
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_statistics(self) -> dict:
        """
        Get validation statistics
        
        Returns:
            dict: Statistics from history
        
        Example:
            >>> stats = validator.get_statistics()
            >>> print(f"Average confidence: {stats['avg_confidence']}")
        """
        if len(self.history) == 0:
            return {
                "total_results": 0,
                "avg_confidence": 0.0,
                "avg_level": 0.0
            }
        
        confidences = [r.confiance for r in self.history]
        percentages = [r.niveau_percentage for r in self.history]
        
        return {
            "total_results": len(self.history),
            "avg_confidence": round(np.mean(confidences), 3),
            "min_confidence": round(np.min(confidences), 3),
            "max_confidence": round(np.max(confidences), 3),
            "avg_level": round(np.mean(percentages), 2),
            "std_level": round(np.std(percentages), 2),
            "methods_used": list(set(r.methode_utilisee for r in self.history))
        }
    
    def clear_history(self):
        """Clear validation history"""
        self.history = []
