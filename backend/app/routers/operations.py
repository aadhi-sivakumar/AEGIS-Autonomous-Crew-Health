from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CrewMember
from ..schemas import OperationsOut
from ..services import operations as operations_service

router = APIRouter(prefix="/api", tags=["operations"])


@router.get("/operations/{astronaut_id}", response_model=OperationsOut)
def get_operations(astronaut_id: str, db: Session = Depends(get_db)):
    if not db.get(CrewMember, astronaut_id):
        raise HTTPException(status_code=404, detail=f"Unknown astronaut: {astronaut_id}")
    return operations_service.build_operations(db, astronaut_id)
