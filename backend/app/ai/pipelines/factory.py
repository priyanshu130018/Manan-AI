from app.ai.pipelines.ingest_pipeline import IngestPipeline
from app.ai.pipelines.query_pipeline import QueryPipeline


class PipelineFactory:
    _ingest_pipeline: IngestPipeline | None = None
    _query_pipeline: QueryPipeline | None = None

    @classmethod
    def get_ingest_pipeline(
        cls,
    ) -> IngestPipeline:
        if cls._ingest_pipeline is None:
            cls._ingest_pipeline = (
                IngestPipeline()
            )

        return cls._ingest_pipeline

    @classmethod
    def get_query_pipeline(
        cls,
    ) -> QueryPipeline:
        if cls._query_pipeline is None:
            cls._query_pipeline = (
                QueryPipeline()
            )

        return cls._query_pipeline