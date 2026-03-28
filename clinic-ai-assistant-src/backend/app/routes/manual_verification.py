from app.services.manual_verification_dashboard import (
    ManualVerificationCoverageInvalid,
    ManualVerificationCoverageUnavailable,
    ManualVerificationTaskNotFound,
    discover_manual_verification_tasks,
    load_manual_verification_coverage,
    save_manual_verification_coverage,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ManualVerificationCoverageUpdate(BaseModel):
    payload: dict


@router.get("/manual-verification/tasks")
def list_manual_verification_tasks():
    return {
        "tasks": discover_manual_verification_tasks(),
    }


@router.get("/manual-verification/tasks/{task_id}")
def get_manual_verification_task(task_id: str):
    try:
        return load_manual_verification_coverage(task_id)
    except ManualVerificationTaskNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ManualVerificationCoverageUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ManualVerificationCoverageInvalid as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/manual-verification/tasks/{task_id}")
def update_manual_verification_task(task_id: str, body: ManualVerificationCoverageUpdate):
    try:
        return save_manual_verification_coverage(task_id, body.payload)
    except ManualVerificationTaskNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ManualVerificationCoverageUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ManualVerificationCoverageInvalid as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
