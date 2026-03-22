from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Company
from app.schemas import CompanyCreate, CompanyUpdate, CompanyResponse
from typing import List
import uuid

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=List[CompanyResponse])
async def list_companies(db: Session = Depends(get_db)):
    """Get all companies"""
    return db.query(Company).all()


@router.post("", response_model=CompanyResponse)
async def create_company(company: CompanyCreate, db: Session = Depends(get_db)):
    """Create a new company to track"""
    db_company = Company(**company.dict())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(company_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get company details"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise ValueError(f"Company {company_id} not found")
    return company


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: uuid.UUID,
    company_update: CompanyUpdate,
    db: Session = Depends(get_db)
):
    """Update company settings"""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise ValueError(f"Company {company_id} not found")
    
    update_data = company_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_company, key, value)
    
    db.commit()
    db.refresh(db_company)
    return db_company


@router.delete("/{company_id}")
async def delete_company(company_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a company"""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise ValueError(f"Company {company_id} not found")
    
    db.delete(db_company)
    db.commit()
    return {"message": "Company deleted"}
