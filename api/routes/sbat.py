import asyncio

from fastapi import APIRouter, Depends, HTTPException

from ..db.base_repo import BaseRepository
from ..dependencies import get_admin_user, get_repo, get_sbat_monitor
from ..models.sbat import ExamTimeSlotRead, MonitorConfiguration, MonitorStatus, SbatRequestRead
from ..services.sbat_monitor import SbatMonitor

router = APIRouter(dependencies=[Depends(get_admin_user)], tags=["SBAT-monitor"])


@router.post("/startup")
async def start_monitoring(config: MonitorConfiguration, sbat_monitor: SbatMonitor = Depends(get_sbat_monitor)) -> MonitorStatus:
    sbat_monitor.config = config
    try:
        await sbat_monitor.start()
    except RuntimeError as re:
        raise HTTPException(409, detail=str(re)) from re
    await asyncio.sleep(3)
    return sbat_monitor.status()


@router.post("/monitor-config")
async def update_monitoring_configurations(
    config: MonitorConfiguration, sbat_monitor: SbatMonitor = Depends(get_sbat_monitor)
) -> MonitorStatus:
    sbat_monitor.config = config
    return sbat_monitor.status()


@router.get("/monitor-status")
async def get_monitoring_status(sbat_monitor: SbatMonitor = Depends(get_sbat_monitor)) -> MonitorStatus:
    return sbat_monitor.status()


@router.get("/shutdown")
async def stop_monitoring(sbat_monitor: SbatMonitor = Depends(get_sbat_monitor)) -> MonitorStatus:
    try:
        await sbat_monitor.stop()
    except RuntimeError as re:
        raise HTTPException(409, detail=str(re)) from re
    return sbat_monitor.status()


@router.get("/requests")
async def get_requests(limit: int = 10, repo: BaseRepository = Depends(get_repo("mongodb"))) -> list[SbatRequestRead]:
    return await repo.list_requests(limit)


@router.get("/exam-time-slots")
async def get_exam_time_slots(limit: int = 10, repo: BaseRepository = Depends(get_repo("mongodb"))) -> list[ExamTimeSlotRead]:
    return await repo.list_time_slots(limit)
