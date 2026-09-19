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
        upload_preset: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self._cloud_name = cloud_name if cloud_name is not None else settings.cloudinary_cloud_name
        self._api_key = api_key if api_key is not None else settings.cloudinary_api_key
        self._api_secret = api_secret if api_secret is not None else settings.cloudinary_api_secret
        self._folder = (folder if folder is not None else (settings.cloudinary_folder or "manan-ai")).strip("/")
        self._upload_preset = upload_preset if upload_preset is not None else settings.cloudinary_upload_preset

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
            raise DocumentProcessingError(
                "Cloudinary credentials are not configured. Please set CLOUDINARY_CLOUD_NAME, "
                "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in your environment configuration."
            )

        target_folder = f"{self._folder}/users/{user_id}/documents/{document_id}"
        ext = Path(filename).suffix.lower()
        # Choose resource_type: raw for docs/PDFs/text; image for image types
        resource_type = "image" if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"} else "raw"

        upload_kwargs: dict[str, Any] = {
            "folder": target_folder,
            "public_id": document_id,
            "resource_type": resource_type,
            "use_filename": False,
            "unique_filename": False,
            "overwrite": True,
        }
        if self._upload_preset:
            upload_kwargs["upload_preset"] = self._upload_preset

        try:
            result = cloudinary.uploader.upload(file_obj, **upload_kwargs)
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
        if not self._configured:
            logger.warning("Cloudinary not configured; cannot delete asset %s", public_id)
            return False
        if not public_id:
            return True

        try:
            res = cloudinary.uploader.destroy(public_id, resource_type=resource_type, invalidate=True)
            result_status = res.get("result")
            if result_status == "ok":
                logger.info("Deleted Cloudinary asset: %s", public_id)
                return True
            elif result_status == "not found" and resource_type == "raw":
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
