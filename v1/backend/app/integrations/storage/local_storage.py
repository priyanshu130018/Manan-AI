from pathlib import Path
from app.core.config import get_settings
from app.core.exceptions import DocumentValidationError


class LocalStorage:
    def __init__(self) -> None:
        settings = get_settings()
        self._upload_dir = Path(settings.documents_dir).resolve()
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    def get_target_path(self, stored_filename: str) -> Path:
        target = (self._upload_dir / stored_filename).resolve()
        # Security: prevent path traversal attacks
        if not str(target).startswith(str(self._upload_dir)):
            raise DocumentValidationError("Invalid storage path traversal detected.")
        return target

    def file_exists(self, stored_filename: str) -> bool:
        return self.get_target_path(stored_filename).exists()

    def delete_file(self, stored_filename: str) -> None:
        target = self.get_target_path(stored_filename)
        if target.exists():
            target.unlink(missing_ok=True)


# Compatibility alias
LocalStorageService = LocalStorage
