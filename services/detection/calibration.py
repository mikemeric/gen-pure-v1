"""
Calibration system for fuel level detection

Provides calibration between:
- Pixels ↔ Millimeters (physical dimensions)
- Pixel position ↔ Volume (mL)
- Percentage ↔ Volume

Supports:
- Linear calibration
- Multi-point calibration
- Polynomial calibration
- Save/load calibration data
"""
import json
import numpy as np
from typing import List, Tuple, Optional, Dict
from pathlib import Path
from datetime import datetime

# Use unified CalibrationPoint from schemas (Pydantic)
from api.schemas.detection import CalibrationPoint


class Calibration:
    """
    Calibration system for fuel level detection
    
    Supports multiple calibration types:
    - Linear (2 points: empty, full)
    - Multi-point (3+ points with interpolation)
    - Polynomial (curve fitting)
    
    Features:
    - Save/load calibration
    - Pixel ↔ Percentage conversion
    - Percentage ↔ Volume conversion
    - Validation
    """
    
    def __init__(
        self,
        image_height: int,
        tank_capacity_ml: float = 1000.0,
        calibration_type: str = "linear"
    ):
        """
        Initialize calibration
        
        Args:
            image_height: Image height in pixels
            tank_capacity_ml: Tank capacity in milliliters
            calibration_type: Type ("linear", "multipoint", "polynomial")
        
        Example:
            >>> cal = Calibration(
            ...     image_height=600,
            ...     tank_capacity_ml=5000.0,
            ...     calibration_type="linear"
            ... )
        """
        self.image_height = image_height
        self.tank_capacity_ml = tank_capacity_ml
        self.calibration_type = calibration_type
        
        self.points: List[CalibrationPoint] = []
        self.is_calibrated = False
        
        # Polynomial coefficients (for polynomial calibration)
        self.poly_coeffs: Optional[np.ndarray] = None
    
    def add_point(
        self,
        pixel_y: int,
        percentage: float,
        volume_ml: Optional[float] = None
    ):
        """
        Add calibration point
        
        Args:
            pixel_y: Y position in pixels
            percentage: Fuel level percentage (0-100)
            volume_ml: Volume in milliliters (optional)
        
        Example:
            >>> cal.add_point(pixel_y=500, percentage=0)    # Empty
            >>> cal.add_point(pixel_y=100, percentage=100)  # Full
        """
        if volume_ml is None:
            volume_ml = (percentage / 100.0) * self.tank_capacity_ml
        
        point = CalibrationPoint(pixel_y, percentage, volume_ml)
        self.points.append(point)
        
        # Sort points by pixel_y (descending: top to bottom)
        self.points.sort(key=lambda p: p.pixel_y, reverse=True)
        
        # Update calibration
        if len(self.points) >= 2:
            self._compute_calibration()
    
    def _compute_calibration(self):
        """Compute calibration from points"""
        if len(self.points) < 2:
            raise ValueError("Need at least 2 calibration points")
        
        if self.calibration_type == "polynomial" and len(self.points) >= 3:
            # Polynomial fit
            x = np.array([p.pixel_y for p in self.points])
            y = np.array([p.percentage for p in self.points])
            
            # Fit polynomial (degree = min(len(points)-1, 3))
            degree = min(len(self.points) - 1, 3)
            self.poly_coeffs = np.polyfit(x, y, degree)
        
        self.is_calibrated = True
    
    def pixel_to_percentage(self, pixel_y: int) -> float:
        """
        Convert pixel Y position to percentage
        
        Args:
            pixel_y: Y position in pixels
        
        Returns:
            float: Fuel level percentage (0-100)
        
        Example:
            >>> percentage = cal.pixel_to_percentage(300)
            >>> print(f"Level: {percentage}%")
        """
        if not self.is_calibrated:
            raise RuntimeError("Calibration not complete. Add at least 2 points.")
        
        if self.calibration_type == "polynomial" and self.poly_coeffs is not None:
            # Polynomial interpolation
            percentage = np.polyval(self.poly_coeffs, pixel_y)
        
        else:
            # Linear or multipoint interpolation
            # Find surrounding points
            below = None
            above = None
            
            for point in self.points:
                if point.pixel_y >= pixel_y:
                    below = point
                else:
                    above = point
                    break
            
            if below is None:
                # Above highest point
                return self.points[0].percentage
            elif above is None:
                # Below lowest point
                return self.points[-1].percentage
            else:
                # Interpolate
                t = (pixel_y - below.pixel_y) / (above.pixel_y - below.pixel_y)
                percentage = below.percentage + t * (above.percentage - below.percentage)
        
        # Clamp to [0, 100]
        return max(0.0, min(100.0, percentage))
    
    def percentage_to_volume(self, percentage: float) -> float:
        """
        Convert percentage to volume
        
        Args:
            percentage: Fuel level percentage (0-100)
        
        Returns:
            float: Volume in milliliters
        
        Example:
            >>> volume = cal.percentage_to_volume(75.5)
            >>> print(f"Volume: {volume} mL")
        """
        return (percentage / 100.0) * self.tank_capacity_ml
    
    def pixel_to_volume(self, pixel_y: int) -> float:
        """
        Convert pixel Y position to volume
        
        Args:
            pixel_y: Y position in pixels
        
        Returns:
            float: Volume in milliliters
        
        Example:
            >>> volume = cal.pixel_to_volume(300)
            >>> print(f"Volume: {volume} mL")
        """
        percentage = self.pixel_to_percentage(pixel_y)
        return self.percentage_to_volume(percentage)
    
    def volume_to_percentage(self, volume_ml: float) -> float:
        """
        Convert volume to percentage
        
        Args:
            volume_ml: Volume in milliliters
        
        Returns:
            float: Fuel level percentage (0-100)
        
        Example:
            >>> percentage = cal.volume_to_percentage(3750)
            >>> print(f"Level: {percentage}%")
        """
        return (volume_ml / self.tank_capacity_ml) * 100.0
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate calibration
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        
        Example:
            >>> is_valid, errors = cal.validate()
            >>> if not is_valid:
            ...     print(f"Errors: {errors}")
        """
        errors = []
        
        # Check minimum points
        if len(self.points) < 2:
            errors.append("Need at least 2 calibration points")
        
        # Check points are within image bounds
        for i, point in enumerate(self.points):
            if point.pixel_y < 0 or point.pixel_y > self.image_height:
                errors.append(f"Point {i}: pixel_y {point.pixel_y} outside image bounds")
        
        # Check percentages are in valid range
        for i, point in enumerate(self.points):
            if point.percentage < 0 or point.percentage > 100:
                errors.append(f"Point {i}: percentage {point.percentage} outside [0, 100]")
        
        # Check monotonicity (percentage should increase as pixel_y decreases)
        for i in range(len(self.points) - 1):
            if self.points[i].percentage <= self.points[i+1].percentage:
                errors.append(f"Points {i} and {i+1}: percentages not monotonically increasing")
        
        return len(errors) == 0, errors
    
    def save(self, filepath: str):
        """
        Save calibration to file
        
        Args:
            filepath: Path to save file (JSON)
        
        Example:
            >>> cal.save("calibration.json")
        """
        data = {
            "image_height": self.image_height,
            "tank_capacity_ml": self.tank_capacity_ml,
            "calibration_type": self.calibration_type,
            "points": [p.dict() for p in self.points],  # Pydantic .dict()
            "is_calibrated": self.is_calibrated,
            "created_at": datetime.now().isoformat()
        }
        
        if self.poly_coeffs is not None:
            data["poly_coeffs"] = self.poly_coeffs.tolist()
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Calibration saved to {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> 'Calibration':
        """
        Load calibration from file
        
        Args:
            filepath: Path to calibration file (JSON)
        
        Returns:
            Calibration: Loaded calibration
        
        Example:
            >>> cal = Calibration.load("calibration.json")
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        cal = cls(
            image_height=data["image_height"],
            tank_capacity_ml=data["tank_capacity_ml"],
            calibration_type=data["calibration_type"]
        )
        
        # Load points
        for point_data in data["points"]:
            point = CalibrationPoint(**point_data)  # Pydantic constructor
            cal.points.append(point)
        
        # Load polynomial coefficients
        if "poly_coeffs" in data:
            cal.poly_coeffs = np.array(data["poly_coeffs"])
        
        cal.is_calibrated = data.get("is_calibrated", False)
        
        print(f"✅ Calibration loaded from {filepath}")
        return cal
    
    def get_info(self) -> dict:
        """
        Get calibration information
        
        Returns:
            dict: Calibration info
        
        Example:
            >>> info = cal.get_info()
            >>> print(f"Points: {info['num_points']}")
            >>> print(f"Type: {info['calibration_type']}")
        """
        return {
            "calibration_type": self.calibration_type,
            "is_calibrated": self.is_calibrated,
            "num_points": len(self.points),
            "image_height": self.image_height,
            "tank_capacity_ml": self.tank_capacity_ml,
            "points": [
                {
                    "pixel_y": p.pixel_y,
                    "percentage": p.percentage,
                    "volume_ml": p.volume_ml
                }
                for p in self.points
            ]
        }


def create_default_calibration(
    image_height: int,
    tank_capacity_ml: float = 1000.0
) -> Calibration:
    """
    Create default linear calibration (empty at bottom, full at top)
    
    Args:
        image_height: Image height in pixels
        tank_capacity_ml: Tank capacity in milliliters
    
    Returns:
        Calibration: Default calibration
    
    Example:
        >>> cal = create_default_calibration(600, 5000.0)
    """
    cal = Calibration(image_height, tank_capacity_ml, calibration_type="linear")
    
    # Default: Empty at bottom (90% of height), Full at top (10% of height)
    cal.add_point(pixel_y=int(image_height * 0.9), percentage=0)    # Empty
    cal.add_point(pixel_y=int(image_height * 0.1), percentage=100)  # Full
    
    return cal
