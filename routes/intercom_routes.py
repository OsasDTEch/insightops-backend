from fastapi import APIRouter


router = APIRouter(prefix="/intercom", tags=["Intercom"])

@router.get('/callback')
async def intercom_callback():
    pass

