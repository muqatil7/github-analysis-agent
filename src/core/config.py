"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # LangSmith Configuration
    langchain_tracing_v2: bool = Field(True, alias="LANGCHAIN_TRACING_V2")
    langchain_api_key: Optional[str] = Field(None, alias="LANGCHAIN_API_KEY")
    langsmith_api_key: Optional[str] = Field(None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field("github-analysis-agent", alias="LANGSMITH_PROJECT")
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o-mini", alias="OPENAI_MODEL")
    openai_temperature: float = Field(0.1, alias="OPENAI_TEMPERATURE")
    
    # GitHub Configuration
    github_token: str = Field(..., alias="GITHUB_PERSONAL_ACCESS_TOKEN")
    
    # Context Management
    max_context_tokens: int = Field(200000, alias="MAX_CONTEXT_TOKENS")
    summary_token_threshold: int = Field(180000, alias="SUMMARY_TOKEN_THRESHOLD")
    keep_last_messages: int = Field(5, alias="KEEP_LAST_MESSAGES")
    
    # Application Settings
    debug: bool = Field(False, alias="DEBUG")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    
    # MCP Server Configuration
    mcp_server_command: str = Field("npx", alias="MCP_SERVER_COMMAND")
    mcp_server_args: str = Field("-y,@modelcontextprotocol/server-github", alias="MCP_SERVER_ARGS")
    
    @validator("mcp_server_args")
    def validate_mcp_args(cls, v):
        """Convert comma-separated string to list."""
        if isinstance(v, str):
            return v.split(",")
        return v
    
    @validator("summary_token_threshold")
    def validate_threshold(cls, v, values):
        """Ensure threshold is less than max tokens."""
        max_tokens = values.get("max_context_tokens", 200000)
        if v >= max_tokens:
            raise ValueError("Summary threshold must be less than max context tokens")
        return v
    
    def get_mcp_config(self) -> dict:
        """Get MCP server configuration."""
        return {
            "GitHub": {
                "command": self.mcp_server_command,
                "args": self.mcp_server_args if isinstance(self.mcp_server_args, list) else self.mcp_server_args.split(","),
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token
                },
                "transport": "stdio"
            }
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()