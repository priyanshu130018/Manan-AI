from app.core.logger import LoggerFactory


class BaseService:
    def __init__(self) -> None:
        self.logger = LoggerFactory.create_logger(
            self.__class__.__name__
        )