"""
Calibration API endpoints

Endpoints:
- POST /api/calibrations - Create new calibration
- GET /api/calibrations - List calibrations
- GET /api/calibrations/{id} - Get calibration details
- PUT /api/calibrations/{id} - Update calibration
- DELETE /api/calibrations/{id} - Delete calibration
"""
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
import json
import tempfile
import os

from api.schemas.detection import (
    CalibrationCreateRequest,
    CalibrationResponse,
    CalibrationListResponse,
    CalibrationPoint as CalibrationPointSchema
)
from api.middleware.auth_middleware import get_current_user
from services.detection.calibration import Calibration, CalibrationPoint


router = APIRouter(prefix="/api/calibrations", tags=["Calibration"])

# In-memory storage for calibrations (replace with database in production)
_calibrations: Dict[str, Calibration] = {}
_calibration_metadata: Dict[str, dict] = {}


def generate_calibration_id() -> str:
    """Generate unique calibration ID"""
    import uuid
    return f"cal_{uuid.uuid4().hex[:12]}"


@router.post(
    "",
    response_model=CalibrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create calibration",
    description="Create new tank calibration"
)
async def create_calibration(
    request: CalibrationCreateRequest,
    user: dict = Depends(get_current_user)
):
    """
    Create new calibration
    
    **Required:**
    - Name
    - Image height (pixels)
    - Tank capacity (milliliters)
    - At least 2 calibration points
    
    **Returns:**
    - Calibration ID
    - Calibration details
    """
    # Create calibration
    calibration = Calibration(
        image_height=request.image_height,
        tank_capacity_ml=request.tank_capacity_ml,
        calibration_type=request.calibration_type
    )
    
    # Add points
    for point in request.points:
        calibration.add_point(
            pixel_y=point.pixel_y,
            percentage=point.percentage,
            volume_ml=point.volume_ml
        )
    
    # Validate
    is_valid, errors = calibration.validate()
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Calibration validation failed: {'; '.join(errors)}"
        )
    
    # Generate ID
    cal_id = generate_calibration_id()
    
    # Store
    _calibrations[cal_id] = calibration
    _calibration_metadata[cal_id] = {
        "name": request.name,
        "created_at": datetime.now(),
        "created_by": user["user_id"]
    }
    
    # Return response
    return _calibration_to_response(cal_id, calibration)


@router.get(
    "",
    response_model=CalibrationListResponse,
    summary="List calibrations",
    description="Get list of all calibrations"
)
async def list_calibrations(
    user: dict = Depends(get_current_user)
):
    """
    List all calibrations
    
    **Returns:**
    - List of calibrations
    - Total count
    """
    calibrations = []
    
    for cal_id, calibration in _calibrations.items():
        response = _calibration_to_response(cal_id, calibration)
        # Don't include points in list view
        response.points = []
        calibrations.append(response)
    
    return CalibrationListResponse(
        calibrations=calibrations,
        total=len(calibrations)
    )


@router.get(
    "/{calibration_id}",
    response_model=CalibrationResponse,
    summary="Get calibration",
    description="Get calibration details by ID"
)
async def get_calibration(
    calibration_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get calibration details
    
    **Parameters:**
    - calibration_id: Calibration ID
    
    **Returns:**
    - Full calibration details including all points
    """
    if calibration_id not in _calibrations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calibration not found: {calibration_id}"
        )
    
    calibration = _calibrations[calibration_id]
    return _calibration_to_response(calibration_id, calibration)


@router.put(
    "/{calibration_id}",
    response_model=CalibrationResponse,
    summary="Update calibration",
    description="Update existing calibration"
)
async def update_calibration(
    calibration_id: str,
    request: CalibrationCreateRequest,
    user: dict = Depends(get_current_user)
):
    """
    Update calibration
    
    **Parameters:**
    - calibration_id: Calibration ID
    
    **Body:**
    - New calibration data
    
    **Returns:**
    - Updated calibration details
    """
    if calibration_id not in _calibrations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calibration not found: {calibration_id}"
        )
    
    # Create new calibration with updated data
    calibration = Calibration(
        image_height=request.image_height,
        tank_capacity_ml=request.tank_capacity_ml,
        calibration_type=request.calibration_type
    )
    
    # Add points
    for point in request.points:
        calibration.add_point(
            pixel_y=point.pixel_y,
            percentage=point.percentage,
            volume_ml=point.volume_ml
        )
    
    # Validate
    is_valid, errors = calibration.validate()
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Calibration validation failed: {'; '.join(errors)}"
        )
    
    # Update
    _calibrations[calibration_id] = calibration
    _calibration_metadata[calibration_id]["name"] = request.name
    _calibration_metadata[calibration_id]["updated_at"] = datetime.now()
    
    return _calibration_to_response(calibration_id, calibration)


@router.delete(
    "/{calibration_id}",
    summary="Delete calibration",
    description="Delete calibration by ID"
)
async def delete_calibration(
    calibration_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Delete calibration
    
    **Parameters:**
    - calibration_id: Calibration ID
    
    **Returns:**
    - Success message
    """
    if calibration_id not in _calibrations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calibration not found: {calibration_id}"
        )
    
    # Check permissions (only creator or admin can delete)
    metadata = _calibration_metadata[calibration_id]
    if metadata["created_by"] != user["user_id"] and "admin" not in user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this calibration"
        )
    
    # Delete
    del _calibrations[calibration_id]
    del _calibration_metadata[calibration_id]
    
    return {"success": True, "message": f"Calibration {calibration_id} deleted"}


@router.post(
    "/{calibration_id}/export",
    summary="Export calibration",
    description="Export calibration to JSON file"
)
async def export_calibration(
    calibration_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Export calibration to JSON
    
    **Parameters:**
    - calibration_id: Calibration ID
    
    **Returns:**
    - JSON file download
    """
    if calibration_id not in _calibrations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calibration not found: {calibration_id}"
        )
    
    calibration = _calibrations[calibration_id]
    
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    calibration.save(temp_file.name)
    
    # Read content
    with open(temp_file.name, 'r') as f:
        content = f.read()
    
    # Cleanup
    os.unlink(temp_file.name)
    
    from fastapi.responses import Response
    
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=calibration_{calibration_id}.json"
        }
    )


def _calibration_to_response(cal_id: str, calibration: Calibration) -> CalibrationResponse:
    """
    Convert Calibration to CalibrationResponse
    
    Args:
        cal_id: Calibration ID
        calibration: Calibration object
    
    Returns:
        CalibrationResponse: API response
    """
    metadata = _calibration_metadata.get(cal_id, {})
    
    # Convert points
    points = [
        CalibrationPointSchema(
            pixel_y=p.pixel_y,
            percentage=p.percentage,
            volume_ml=p.volume_ml
        )
        for p in calibration.points
    ]
    
    return CalibrationResponse(
        id=cal_id,
        name=metadata.get("name", "Unknown"),
        calibration_type=calibration.calibration_type,
        is_calibrated=calibration.is_calibrated,
        num_points=len(calibration.points),
        image_height=calibration.image_height,
        tank_capacity_ml=calibration.tank_capacity_ml,
        created_at=metadata.get("created_at", datetime.now()),
        points=points
    )
