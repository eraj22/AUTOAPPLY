from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import UserSettings
from ..schemas import (
    UserSettingsResponse,
    UserSettingsCreate,
    UserSettingsUpdate,
)

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
)


@router.get("/", response_model=UserSettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    """
    Get the user settings. Returns the first/default settings record.
    If no settings exist, creates a default one.
    """
    settings = db.query(UserSettings).first()
    
    if not settings:
        # Create default settings if none exist
        default_settings = UserSettings(
            notification_email='user@example.com',
            global_mode='approval',
            fit_score_threshold=65,
            auto_apply_threshold=75,
            daily_digest_time='08:00',
            scrape_interval_hours=6
        )
        db.add(default_settings)
        db.commit()
        db.refresh(default_settings)
        return default_settings
    
    return settings


@router.post("/", response_model=UserSettingsResponse, status_code=status.HTTP_201_CREATED)
def create_settings(
    settings_data: UserSettingsCreate,
    db: Session = Depends(get_db),
):
    """
    Create new user settings.
    """
    settings = UserSettings(**settings_data.dict())
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


@router.put("/{settings_id}", response_model=UserSettingsResponse)
def update_settings(
    settings_id: str,
    settings_update: UserSettingsUpdate,
    db: Session = Depends(get_db),
):
    """
    Update specific settings by ID.
    """
    settings = db.query(UserSettings).filter(UserSettings.id == settings_id).first()
    
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Settings with id {settings_id} not found",
        )
    
    update_data = settings_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


@router.delete("/{settings_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_settings(
    settings_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete settings by ID.
    """
    settings = db.query(UserSettings).filter(UserSettings.id == settings_id).first()
    
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Settings with id {settings_id} not found",
        )
    
    db.delete(settings)
    db.commit()
