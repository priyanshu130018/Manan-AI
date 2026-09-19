import os
from pathlib import Path
from typing import Any, BinaryIO, Optional, Union
import cloudinary
import cloudinary.uploader
import cloudinary.utils

from app.core.config import get_settings
from app.core.exceptions import DocumentProcessingError
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("CloudinaryStorage")


class CloudinaryStorage:
    """Manages document uploads and deletions using Cloudinary cloud storage."""

    def __init__(
        self,
        cloud_name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        folder: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self._cloud_name = cloud_name or settings.cloudinary_cloud_name
        self._api_key = api_key or settings.cloudinary_api_key
        self._api_secret = api_secret or settings.cloudinary_api_secret
        self._folder = (folder or settings.cloudinary_folder or "manan-ai").strip("/")

        if self._cloud_name and self._api_key and self._api_secret:
            cloudinary.config(
                cloud_name=self._cloud_name,
                api_key=self._api_key,
                api_secret=self._api_secret,
                secure=True,
            )
            self._configured = True
        else:
            self._configured = False
            logger.warning("Cloudinary credentials not fully configured. Cloud uploads will require CLOUDINARY_* environment variables.")

    @property
    def is_configured(self) -> bool:
        return self._configured

    def upload_file(
        self,
        file_obj: Union[str, Path, BinaryIO, bytes],
        filename: str,
        user_id: str,
        document_id: str,
    ) -> dict[str, Any]:
        """Upload a document to Cloudinary under folder manan-ai/users/{user_id}/documents/{document_id}."""
        if not self._configured:
            # Fallback mock/simulated object for local offline testing when Cloudinary credentials are absent
            logger.warning("Cloudinary not configured; simulating asset upload for document %s", document_id)
            return {
                "cloudinary_public_id": f"{self._folder}/users/{user_id}/documents/{document_id}/{document_id}",
                "cloudinary_secure_url": f"https://res.cloudinary.com/simulated/raw/upload/{self._folder}/users/{user_id}/documents/{document_id}/{document_id}",
                "cloudinary_resource_type": "raw",
            }

        target_folder = f"{self._folder}/users/{user_id}/documents/{document_id}"
        ext = Path(filename).suffix.lower()
        # Choose resource_type: raw for docs/PDFs/text; image for image types
        resource_type = "image" if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"} else "raw"

        try:
            result = cloudinary.uploader.upload(
                file_obj,
                folder=target_folder,
                public_id=document_id,
                resource_type=resource_type,
                use_filename=False,
                unique_filename=False,
                overwrite=True,
            )
            logger.info("Uploaded document '%s' to Cloudinary (public_id=%s)", filename, result.get("public_id"))
            return {
                "cloudinary_public_id": result.get("public_id"),
                "cloudinary_secure_url": result.get("secure_url"),
                "cloudinary_resource_type": result.get("resource_type", resource_type),
            }
        except Exception as e:
            logger.exception("Cloudinary upload failed for '%s': %s", filename, e)
            raise DocumentProcessingError(f"Failed to upload document to Cloudinary storage: {e}") from e

    def delete_file(self, public_id: str, resource_type: str = "raw") -> bool:
        """Destroy an asset on Cloudinary by its public ID."""
        if not self._configured or not public_id:
            logger.info("Skipping Cloudinary destroy for %s (configured=%s)", public_id, self._configured)
            return True

        try:
            res = cloudinary.uploader.destroy(public_id, resource_type=resource_type, invalidate=True)
            result_status = res.get("result")
            if result_status == "ok":
                logger.info("Deleted Cloudinary asset: %s", public_id)
                return True
            elif result_status == "not found" and resource_type == "raw":
                # Retry with image/auto resource_type just in case
                res_alt = cloudinary.uploader.destroy(public_id, resource_type="image", invalidate=True)
                return res_alt.get("result") == "ok" or res_alt.get("result") == "not found"
            logger.warning("Cloudinary delete response for %s: %s", public_id, res)
            return result_status in {"ok", "not found"}
        except Exception as e:
            logger.error("Failed to delete Cloudinary asset '%s': %s", public_id, e)
            return False

    def get_secure_url(self, public_id: str, resource_type: str = "raw") -> str:
        """Construct secure Cloudinary delivery URL for an asset."""
        if not self._configured or not public_id:
            return ""
        return cloudinary.utils.cloudinary_url(
            public_id,
            resource_type=resource_type,
            secure=True,
        )[0]
