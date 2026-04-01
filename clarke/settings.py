"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLARKE_")

    postgres_url: str = "postgresql+asyncpg://clarke:clarke_dev@localhost:5432/clarke"
    pool_size: int = 10
    echo: bool = False


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLARKE_")

    default_answer_model: str = "gpt-4o-mini"
    default_router_model: str = "gpt-4o-mini"
    fallback_model: str = "gpt-3.5-turbo"
    litellm_master_key: str = ""
    answer_temperature: float = 0.0
    request_timeout_ms: int = 30000
    max_retries: int = 3


class TelemetrySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLARKE_")

    otel_endpoint: str = "http://localhost:4317"
    phoenix_endpoint: str = "http://localhost:6006"
    log_level: str = "debug"
    otel_enabled: bool = False


class RetrievalSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLARKE_")

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334
    qdrant_api_key: str = ""
    qdrant_collection: str = "clarke_chunks"
    search_top_k: int = 20
    rerank_top_k: int = 5
    rerank_enabled: bool = True
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class EmbeddingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLARKE_")

    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 64


class BrokerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLARKE_")

    max_retrieval_loops: int = 1
    max_subagent_depth: int = 5
    max_active_subagents_per_root: int = 10
    default_request_timeout_ms: int = 800


class LearningSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLARKE_")

    attribution_overlap_threshold: float = 0.15
    weight_learning_rate: float = 0.05
    epsilon_initial: float = 0.10
    epsilon_min: float = 0.05
    epsilon_decay_rate: float = 0.995
    allowed_context_request_sources: list[str] = [
        "docs",
        "memory",
        "decisions",
        "recent_history",
        "policy",
    ]
    max_context_request_items: int = 5
    second_pass_budget_fraction: float = 0.6
    groundedness_model: str = "gpt-4o-mini"
    groundedness_enabled: bool = False


class TaxonomySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLARKE_")

    min_cluster_size: int = 5
    min_members_for_promotion: int = 30
    min_stability_score: float = 0.75
    stability_window_days: int = 7
    clustering_enabled: bool = True


class GraphSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLARKE_")

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "clarke_dev"
    neo4j_database: str = "neo4j"
    graph_traversal_max_hops: int = 2
    graph_retrieval_top_k: int = 10
    graph_enabled: bool = True


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLARKE_")

    env: str = Field(default="development")

    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    telemetry: TelemetrySettings = Field(default_factory=TelemetrySettings)
    broker: BrokerSettings = Field(default_factory=BrokerSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    learning: LearningSettings = Field(default_factory=LearningSettings)
    graph: GraphSettings = Field(default_factory=GraphSettings)
    taxonomy: TaxonomySettings = Field(default_factory=TaxonomySettings)


@lru_cache
def get_settings() -> Settings:
    return Settings()
