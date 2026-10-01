from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.modules.locations import schemas, service
from app.modules.admin.router import get_current_admin

router = APIRouter(tags=["Locations & Boundaries"])

# --- PUBLIC / USER ENDPOINTS ---

@router.get("/locations/allowed", response_model=List[schemas.AllowedLocationResponse])
async def get_allowed_locations():
    """
    Get all active allowed locations for PowerSystem launch areas.
    Publicly accessible so mobile and web clients can enforce location restrictions.
    """
    return await service.get_active_locations()

@router.post("/locations/validate", response_model=schemas.ValidateLocationResponse)
async def validate_location(req: schemas.ValidateLocationRequest):
    """
    Validate whether a coordinate (lat, lon) falls within an approved launch location.
    """
    is_allowed, matched = await service.is_location_allowed(req.latitude, req.longitude)
    if is_allowed:
        return schemas.ValidateLocationResponse(
            is_allowed=True,
            matched_location=matched,
            message=f"Location is within approved launch territory: {matched}."
        )
    else:
        return schemas.ValidateLocationResponse(
            is_allowed=False,
            matched_location=None,
            message="Location is outside approved PowerSystem launch areas. We currently only operate in Perth, WA."
        )

# --- ADMIN MANAGEMENT ENDPOINTS ---

@router.get("/admin/locations", response_model=schemas.PaginatedAllowedLocationResponse)
async def list_admin_locations(admin=Depends(get_current_admin)):
    """
    List all allowed locations (active & inactive) for Power Admin dashboard.
    """
    items = await service.get_all_locations()
    return schemas.PaginatedAllowedLocationResponse(
        total=len(items),
        items=items
    )

@router.post("/admin/locations", response_model=schemas.AllowedLocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(data: schemas.AllowedLocationCreate, admin=Depends(get_current_admin)):
    """
    Add a new approved location/city to PowerSystem.
    """
    return await service.create_location(data)

@router.put("/admin/locations/{location_id}", response_model=schemas.AllowedLocationResponse)
async def update_location(location_id: int, data: schemas.AllowedLocationUpdate, admin=Depends(get_current_admin)):
    """
    Update details (name, coordinates, radius, state, country) of an existing location.
    """
    return await service.update_location(location_id, data)

@router.patch("/admin/locations/{location_id}/toggle", response_model=schemas.AllowedLocationResponse)
async def toggle_location(location_id: int, admin=Depends(get_current_admin)):
    """
    Toggle a location's active status (e.g. enable or temporarily disable launch in a city).
    """
    return await service.toggle_location_active(location_id)

@router.delete("/admin/locations/{location_id}")
async def delete_location(location_id: int, admin=Depends(get_current_admin)):
    """
    Remove an allowed location from the system.
    """
    return await service.delete_location(location_id)
