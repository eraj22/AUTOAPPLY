from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import UserSettings
from app.schemas import UserSettingsCreate, UserSettingsUpdate, UserSettingsResponse
from typing import Optional
import uuid

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=Optional[UserSettingsResponse])
async def get_settings(db: Session = Depends(get_db)):
    """Get user settings"""
    settings = db.query(UserSettings).first()
    return settings


@router.post("", response_model=UserSettingsResponse)
async def create_settings(settings: UserSettingsCreate, db: Session = Depends(get_db)):
    """Create user settings"""
    existing = db.query(UserSettings).first()
    if existing:
        # Update existing
        update_data = settings.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    
    db_settings = UserSettings(**settings.dict())
    db.add(db_settings)
    db.commit()
    db.refresh(db_settings)
    return db_settings


@router.put("", response_model=UserSettingsResponse)
async def update_settings(
    settings_update: UserSettingsUpdate,
    db: Session = Depends(get_db)
):
    """Update user settings"""
    db_settings = db.query(UserSettings).first()
    if not db_settings:
        raise ValueError("Settings not found. Create settings first.")
    
    update_data = settings_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_settings, key, value)
    
    db.commit()
    db.refresh(db_settings)
    return db_settings
