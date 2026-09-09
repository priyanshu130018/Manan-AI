from pathlib import Path

from fastapi import UploadFile

from app.ai.pipelines.factory import PipelineFactory
from app.core.config import get_settings
from app.schemas.upload import UploadData
from app.schemas.upload import UploadResponse
from app.services.base_service import BaseService


class UploadService(BaseService):
    def __init__(self) -> None:
        super().__init__()

        self._settings = get_settings()
        self._pipeline = PipelineFactory.get_ingest_pipeline()
        

    async def process(self, file: UploadFile,) -> UploadResponse:

        upload_path = (Path(self._settings.upload_dir) / file.filename)

        content = await file.read()

        upload_path.parent.mkdir(parents=True, exist_ok=True,)

        upload_path.write_bytes(content)

        result = await self._pipeline.run(
            str(upload_path),
        )

        return UploadResponse(
            success=True,
            message="File uploaded and indexed successfully.",
            data=UploadData(
                document_id=result["document_id"],
                filename=result["filename"],
                chunks=result["chunks"],
            ),
        )


upload_service = UploadService()