from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    tavily_api_key: str = ""
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "agent_memory"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    max_history_tokens: int = 4000
    max_iterations: int = 10

    model_config = {"env_file": ".env"}


settings = Settings()
