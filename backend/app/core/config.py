from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "NOC Alert Management"
    app_version: str = "0.1.0"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    database_url: str = Field(
        default="postgresql+asyncpg://noc:noc_dev_password@localhost:5432/noc_db"
    )
    database_pool_size: int = Field(default=10)
    database_max_overflow: int = Field(default=20)

    redis_url: str = Field(default="redis://localhost:6379/0")

    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default=["http://localhost:3000"])

    grafana_webhook_secret: str | None = Field(default=None)

    triage_dedup_window_minutes: int = Field(default=15)
    triage_correlation_window_minutes: int = Field(default=10)
    triage_correlation_min_group_size: int = Field(default=3)
    triage_classification_rules_path: str | None = Field(default=None)

    anthropic_api_key: str | None = Field(default=None)

    jira_url: str | None = Field(default=None)
    jira_user: str | None = Field(default=None)
    jira_token: str | None = Field(default=None)
    jira_project_key: str | None = Field(default=None)
    jira_issue_type: str = Field(default="Task")
    jira_webhook_secret: str | None = Field(default=None)
    jira_custom_field_ids: dict[str, str] = Field(
        default_factory=lambda: {
            "incident_id": "customfield_10100",
            "category": "customfield_10101",
            "confidence": "customfield_10102",
            "hypothesis": "customfield_10103",
            "suggested_action": "customfield_10104",
            "resolution_category": "customfield_10105",
            "was_hypothesis_correct": "customfield_10106",
            "actual_resolution_details": "customfield_10107",
        }
    )


settings = Settings()
