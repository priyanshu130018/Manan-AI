from pathlib import Path
from app.core.config import get_settings
from app.core.exceptions import DocumentValidationError


class LocalStorage:
    def __init__(self) -> None:
        settings = get_settings()
        self._upload_dir = Path(settings.documents_dir).resolve()
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    def get_target_path(self, stored_filename: str, user_id: str | None = None) -> Path:
        if user_id:
            user_dir = (self._upload_dir / f"user_{user_id}").resolve()
            user_dir.mkdir(parents=True, exist_ok=True)
            target = (user_dir / stored_filename).resolve()
            if not str(target).startswith(str(user_dir)):
                raise DocumentValidationError("Invalid storage path traversal detected.")
            return target
        
        target = (self._upload_dir / stored_filename).resolve()
        # Security: prevent path traversal attacks
        if not str(target).startswith(str(self._upload_dir)):
            raise DocumentValidationError("Invalid storage path traversal detected.")
        return target

    def file_exists(self, stored_filename: str, user_id: str | None = None) -> bool:
        path = self.get_target_path(stored_filename, user_id=user_id)
        if path.exists():
            return True
        # Legacy fallback if stored directly in upload_dir
        if user_id:
            legacy_path = (self._upload_dir / stored_filename).resolve()
            return legacy_path.exists()
        return False

    def delete_file(self, stored_filename: str, user_id: str | None = None) -> None:
        target = self.get_target_path(stored_filename, user_id=user_id)
        if target.exists():
            target.unlink(missing_ok=True)
            return
        if user_id:
            legacy_target = (self._upload_dir / stored_filename).resolve()
            if legacy_target.exists():
                legacy_target.unlink(missing_ok=True)



# Compatibility alias
LocalStorageService = LocalStorage
