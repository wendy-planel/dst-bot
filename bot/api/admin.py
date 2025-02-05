import structlog
from fastapi import APIRouter, Body, Query

from bot import models


router = APIRouter()
log = structlog.get_logger()


@router.post("")
async def create(
    qq: str = Body(embed=True, description="QQ号"),
):
    admin = await models.Admin.get_or_none(uid=qq)
    if admin is None:
        return await models.Admin.create(uid=qq)
    else:
        return admin


@router.delete("")
async def remove(
    qq: str = Query(),
):
    return await models.Admin.filter(uid=qq).delete()
