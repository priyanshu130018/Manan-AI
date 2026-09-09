from fastapi import APIRouter
from fastapi import File
from fastapi import UploadFile

from app.schemas.upload import UploadResponse
from app.services.upload_service import upload_service

router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
)


@router.post(
    "",
    response_model=UploadResponse,
)
async def upload(
    file: UploadFile = File(...),
) -> UploadResponse:
    return await upload_service.process(file)