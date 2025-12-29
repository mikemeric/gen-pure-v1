"""
Pydantic schemas for detection API

Request and response models for:
- Detection endpoints
- Calibration endpoints
- History endpoints
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


# ============================================================================
# DETECTION SCHEMAS
# ============================================================================

class DetectionRequest(BaseModel):
    """Request for fuel level detection"""
    
    method: Optional[str] = Field(
        default="ensemble",
        description="Detection method: hough, clustering, edge, ensemble"
    )
    use_preprocessing: Optional[bool] = Field(
        default=True,
        description="Apply preprocessing pipeline"
    )
    calibration_id: Optional[str] = Field(
        default=None,
        description="Calibration ID to use (optional)"
    )
    
    @validator('method')
    def validate_method(cls, v):
        """Validate detection method"""
        allowed = ['hough', 'clustering', 'edge', 'ensemble']
        if v not in allowed:
            raise ValueError(f"Method must be one of: {', '.join(allowed)}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "method": "ensemble",
                "use_preprocessing": True,
                "calibration_id": "default"
            }
        }


class DetectionResponse(BaseModel):
    """Response from fuel level detection"""
    
    success: bool = Field(description="Detection success status")
    niveau_y: int = Field(description="Fuel level Y position in pixels")
    niveau_percentage: float = Field(description="Fuel level percentage (0-100)")
    niveau_ml: Optional[float] = Field(None, description="Fuel volume in milliliters")
    confiance: float = Field(description="Confidence score (0-1)")
    methode_utilisee: str = Field(description="Detection method used")
    temps_traitement_ms: float = Field(description="Processing time in milliseconds")
    image_width: int = Field(description="Image width in pixels")
    image_height: int = Field(description="Image height in pixels")
    timestamp: datetime = Field(description="Detection timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    from_cache: bool = Field(default=False, description="Whether result was served from cache")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "niveau_y": 300,
                "niveau_percentage": 50.5,
                "niveau_ml": 2525.0,
                "confiance": 0.875,
                "methode_utilisee": "ensemble",
                "temps_traitement_ms": 342.5,
                "image_width": 800,
                "image_height": 600,
                "timestamp": "2024-12-14T10:30:00Z",
                "metadata": {
                    "preprocessing": ["resize", "denoise", "enhance"],
                    "calibration_used": True
                },
                "from_cache": False
            }
        }


# ============================================================================
# CALIBRATION SCHEMAS
# ============================================================================

class CalibrationPoint(BaseModel):
    """Single calibration point"""
    
    pixel_y: int = Field(description="Y position in pixels", ge=0)
    percentage: float = Field(description="Fuel level percentage", ge=0, le=100)
    volume_ml: Optional[float] = Field(None, description="Volume in milliliters")
    
    class Config:
        schema_extra = {
            "example": {
                "pixel_y": 540,
                "percentage": 0.0,
                "volume_ml": 0.0
            }
        }


class CalibrationCreateRequest(BaseModel):
    """Request to create new calibration"""
    
    name: str = Field(description="Calibration name")
    image_height: int = Field(description="Image height in pixels", gt=0)
    tank_capacity_ml: float = Field(description="Tank capacity in milliliters", gt=0)
    calibration_type: str = Field(
        default="linear",
        description="Calibration type: linear, multipoint, polynomial"
    )
    points: List[CalibrationPoint] = Field(
        description="Calibration points (min 2)",
        min_items=2
    )
    
    @validator('calibration_type')
    def validate_type(cls, v):
        """Validate calibration type"""
        allowed = ['linear', 'multipoint', 'polynomial']
        if v not in allowed:
            raise ValueError(f"Type must be one of: {', '.join(allowed)}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Tank 50L",
                "image_height": 600,
                "tank_capacity_ml": 50000.0,
                "calibration_type": "linear",
                "points": [
                    {"pixel_y": 540, "percentage": 0.0},
                    {"pixel_y": 60, "percentage": 100.0}
                ]
            }
        }


class CalibrationResponse(BaseModel):
    """Response with calibration details"""
    
    id: str = Field(description="Calibration ID")
    name: str = Field(description="Calibration name")
    calibration_type: str = Field(description="Calibration type")
    is_calibrated: bool = Field(description="Calibration status")
    num_points: int = Field(description="Number of calibration points")
    image_height: int = Field(description="Image height in pixels")
    tank_capacity_ml: float = Field(description="Tank capacity in milliliters")
    created_at: datetime = Field(description="Creation timestamp")
    points: List[CalibrationPoint] = Field(description="Calibration points")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "cal_123456",
                "name": "Tank 50L",
                "calibration_type": "linear",
                "is_calibrated": True,
                "num_points": 2,
                "image_height": 600,
                "tank_capacity_ml": 50000.0,
                "created_at": "2024-12-14T10:00:00Z",
                "points": [
                    {"pixel_y": 540, "percentage": 0.0, "volume_ml": 0.0},
                    {"pixel_y": 60, "percentage": 100.0, "volume_ml": 50000.0}
                ]
            }
        }


class CalibrationListResponse(BaseModel):
    """Response with list of calibrations"""
    
    calibrations: List[CalibrationResponse] = Field(description="List of calibrations")
    total: int = Field(description="Total count")
    
    class Config:
        schema_extra = {
            "example": {
                "calibrations": [
                    {
                        "id": "cal_123456",
                        "name": "Tank 50L",
                        "calibration_type": "linear",
                        "is_calibrated": True,
                        "num_points": 2,
                        "image_height": 600,
                        "tank_capacity_ml": 50000.0,
                        "created_at": "2024-12-14T10:00:00Z",
                        "points": []
                    }
                ],
                "total": 1
            }
        }


# ============================================================================
# HISTORY SCHEMAS
# ============================================================================

class DetectionHistoryQuery(BaseModel):
    """Query parameters for detection history"""
    
    skip: int = Field(default=0, ge=0, description="Skip N records")
    limit: int = Field(default=10, ge=1, le=100, description="Limit results")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    min_confidence: Optional[float] = Field(None, ge=0, le=1, description="Min confidence")
    method: Optional[str] = Field(None, description="Filter by detection method")
    
    class Config:
        schema_extra = {
            "example": {
                "skip": 0,
                "limit": 10,
                "start_date": "2024-12-01T00:00:00Z",
                "end_date": "2024-12-14T23:59:59Z",
                "min_confidence": 0.7,
                "method": "ensemble"
            }
        }


class DetectionHistoryResponse(BaseModel):
    """Response with detection history"""
    
    results: List[DetectionResponse] = Field(description="Detection results")
    total: int = Field(description="Total count")
    skip: int = Field(description="Skip offset")
    limit: int = Field(description="Limit")
    
    class Config:
        schema_extra = {
            "example": {
                "results": [
                    {
                        "success": True,
                        "niveau_percentage": 50.5,
                        "confiance": 0.875,
                        "methode_utilisee": "ensemble",
                        "timestamp": "2024-12-14T10:30:00Z"
                    }
                ],
                "total": 1,
                "skip": 0,
                "limit": 10
            }
        }


# ============================================================================
# STATISTICS SCHEMAS
# ============================================================================

class DetectionStatistics(BaseModel):
    """Detection statistics"""
    
    total_detections: int = Field(description="Total number of detections")
    avg_confidence: float = Field(description="Average confidence score")
    avg_level: float = Field(description="Average fuel level percentage")
    avg_processing_time_ms: float = Field(description="Average processing time")
    methods_used: Dict[str, int] = Field(description="Count by method")
    last_detection: Optional[datetime] = Field(None, description="Last detection time")
    
    class Config:
        schema_extra = {
            "example": {
                "total_detections": 150,
                "avg_confidence": 0.842,
                "avg_level": 62.3,
                "avg_processing_time_ms": 345.2,
                "methods_used": {
                    "ensemble": 120,
                    "hough": 15,
                    "clustering": 10,
                    "edge": 5
                },
                "last_detection": "2024-12-14T10:30:00Z"
            }
        }


# ============================================================================
# ERROR SCHEMAS
# ============================================================================

class ErrorResponse(BaseModel):
    """Error response"""
    
    success: bool = Field(default=False, description="Always false for errors")
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": "ValidationError",
                "message": "Invalid detection method",
                "details": {
                    "field": "method",
                    "value": "invalid_method"
                },
                "timestamp": "2024-12-14T10:30:00Z"
            }
        }
