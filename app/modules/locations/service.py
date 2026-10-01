import math
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from app.core.db import db
from app.modules.locations import schemas

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) in Kilometers.
    """
    R = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

async def get_active_locations() -> List[dict]:
    """
    Fetch all active approved locations.
    """
    if hasattr(db, 'allowedlocation'):
        records = await db.allowedlocation.find_many(
            where={"isActive": True},
            order={"name": "asc"}
        )
        return [r.model_dump() for r in records]
    else:
        rows = await db.query_raw('''
            SELECT id, name, state, country, latitude, longitude, "radiusKm", "isActive", "createdAt", "updatedAt"
            FROM "allowed_locations"
            WHERE "isActive" = true
            ORDER BY name ASC;
        ''')
        return rows or []

async def get_all_locations() -> List[dict]:
    """
    Fetch all approved locations (active and inactive) for admin management.
    """
    if hasattr(db, 'allowedlocation'):
        records = await db.allowedlocation.find_many(
            order={"name": "asc"}
        )
        return [r.model_dump() for r in records]
    else:
        rows = await db.query_raw('''
            SELECT id, name, state, country, latitude, longitude, "radiusKm", "isActive", "createdAt", "updatedAt"
            FROM "allowed_locations"
            ORDER BY name ASC;
        ''')
        return rows or []

async def is_location_allowed(lat: float, lon: float) -> Tuple[bool, Optional[str]]:
    """
    Check if a given coordinate falls within the radius of ANY active approved location.
    Defaults to Perth (-31.9505, 115.8605, 60km) if no locations are found in DB.
    """
    active_locs = await get_active_locations()
    
    if not active_locs:
        # Hard fallback for Perth initial launch
        dist = calculate_haversine_distance(lat, lon, -31.9505, 115.8605)
        if dist <= 60.0:
            return True, "Perth, WA, Australia"
        return False, None

    for loc in active_locs:
        loc_lat = float(loc.get("latitude") or 0.0)
        loc_lon = float(loc.get("longitude") or 0.0)
        radius = float(loc.get("radiusKm") or 60.0)
        
        distance = calculate_haversine_distance(lat, lon, loc_lat, loc_lon)
        if distance <= radius:
            return True, f"{loc.get('name')}, {loc.get('state')}, {loc.get('country')}"

    return False, None

async def create_location(data: schemas.AllowedLocationCreate) -> dict:
    """
    Create a new allowed location.
    """
    # Check if duplicate name exists
    if hasattr(db, 'allowedlocation'):
        existing = await db.allowedlocation.find_unique(where={"name": data.name})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Location '{data.name}' already exists."
            )
        record = await db.allowedlocation.create(
            data={
                "name": data.name,
                "state": data.state,
                "country": data.country,
                "latitude": data.latitude,
                "longitude": data.longitude,
                "radiusKm": data.radiusKm,
                "isActive": data.isActive
            }
        )
        return record.model_dump()
    else:
        existing = await db.query_raw('''
            SELECT id FROM "allowed_locations" WHERE name = $1 LIMIT 1;
        ''', data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Location '{data.name}' already exists."
            )
        rows = await db.query_raw('''
            INSERT INTO "allowed_locations" (name, state, country, latitude, longitude, "radiusKm", "isActive", "createdAt", "updatedAt")
            VALUES ($1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, name, state, country, latitude, longitude, "radiusKm", "isActive", "createdAt", "updatedAt";
        ''', data.name, data.state, data.country, data.latitude, data.longitude, data.radiusKm, data.isActive)
        return rows[0] if rows else {}

async def update_location(location_id: int, data: schemas.AllowedLocationUpdate) -> dict:
    """
    Update an allowed location's properties.
    """
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update.")

    if hasattr(db, 'allowedlocation'):
        existing = await db.allowedlocation.find_unique(where={"id": location_id})
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")
        record = await db.allowedlocation.update(
            where={"id": location_id},
            data=update_data
        )
        return record.model_dump()
    else:
        existing = await db.query_raw('SELECT id FROM "allowed_locations" WHERE id = $1;', location_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")
            
        set_clauses = []
        values = []
        for i, (k, v) in enumerate(update_data.items(), start=1):
            col_name = f'"{k}"' if k in ["radiusKm", "isActive"] else k
            set_clauses.append(f"{col_name} = ${i}")
            values.append(v)
            
        set_clauses.append('"updatedAt" = CURRENT_TIMESTAMP')
        query = f'''
            UPDATE "allowed_locations"
            SET {', '.join(set_clauses)}
            WHERE id = ${len(values) + 1}
            RETURNING id, name, state, country, latitude, longitude, "radiusKm", "isActive", "createdAt", "updatedAt";
        '''
        values.append(location_id)
        rows = await db.query_raw(query, *values)
        return rows[0] if rows else {}

async def toggle_location_active(location_id: int) -> dict:
    """
    Toggle the isActive boolean for a location.
    """
    if hasattr(db, 'allowedlocation'):
        existing = await db.allowedlocation.find_unique(where={"id": location_id})
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")
        record = await db.allowedlocation.update(
            where={"id": location_id},
            data={"isActive": not existing.isActive}
        )
        return record.model_dump()
    else:
        existing = await db.query_raw('SELECT id, "isActive" FROM "allowed_locations" WHERE id = $1;', location_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")
        new_active = not existing[0].get("isActive", True)
        rows = await db.query_raw('''
            UPDATE "allowed_locations"
            SET "isActive" = $1, "updatedAt" = CURRENT_TIMESTAMP
            WHERE id = $2
            RETURNING id, name, state, country, latitude, longitude, "radiusKm", "isActive", "createdAt", "updatedAt";
        ''', new_active, location_id)
        return rows[0] if rows else {}

async def delete_location(location_id: int) -> dict:
    """
    Delete an allowed location.
    """
    if hasattr(db, 'allowedlocation'):
        existing = await db.allowedlocation.find_unique(where={"id": location_id})
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")
        await db.allowedlocation.delete(where={"id": location_id})
        return {"message": f"Location '{existing.name}' deleted successfully"}
    else:
        existing = await db.query_raw('SELECT id, name FROM "allowed_locations" WHERE id = $1;', location_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")
        loc_name = existing[0].get("name", "")
        await db.execute_raw('DELETE FROM "allowed_locations" WHERE id = $1;', location_id)
        return {"message": f"Location '{loc_name}' deleted successfully"}
