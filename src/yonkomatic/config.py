"""Load yonkomatic configuration from config.yaml plus a .env file.

The schema mirrors config.yaml one-to-one. Environment-variable references
(``*_env`` fields) name the variable to read at runtime — they are NOT
resolved here; callers (e.g. publishers) read os.environ themselves so that
configuration objects stay free of secrets.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class ContentConfig(BaseModel):
    base_dir: Path = Path("./content")
    prompt_filename: str = "prompt.md"
    images_dir: str = "images"
    max_images: int = 10

    def prompt_path(self, base: Path | None = None) -> Path:
        return (base or self.base_dir) / self.prompt_filename

    def images_path(self, base: Path | None = None) -> Path:
        return (base or self.base_dir) / self.images_dir


class AIConfig(BaseModel):
    text_model: str = "gpt-5.4"
    image_model: str = "gpt-image-1"
    # OpenAI image API takes pixel sizes (e.g. "1024x1024", "1024x1536", "1536x1024").
    image_size: str = "1024x1536"
    # JPEG q=90 を本番採用: 4 コマ漫画 (assets/demo 実測) で
    # PNG 比 -83% / 線・フキダシの劣化なし。WebP 不採用は Slack
    # プレビューが webp 非対応のクライアントを残すため。
    image_format: Literal["png", "jpeg", "webp"] = "jpeg"
    image_compression: int = Field(default=90, ge=0, le=100)
    max_image_retries: int = 3
    openai_api_key_env: str = "OPENAI_API_KEY"


class SlackPublisherConfig(BaseModel):
    enabled: bool = False
    channel_env: str = "SLACK_CHANNEL_ID"
    token_env: str = "SLACK_BOT_TOKEN"


class DiscordPublisherConfig(BaseModel):
    enabled: bool = False
    webhook_env: str = "DISCORD_WEBHOOK_URL"


class StaticSitePublisherConfig(BaseModel):
    enabled: bool = False
    output_dir: Path = Path("./docs")
    base_url: str = ""


class PublishersConfig(BaseModel):
    slack: SlackPublisherConfig = Field(default_factory=SlackPublisherConfig)
    discord: DiscordPublisherConfig = Field(default_factory=DiscordPublisherConfig)
    static_site: StaticSitePublisherConfig = Field(default_factory=StaticSitePublisherConfig)


class ScheduleConfig(BaseModel):
    timezone: str = "Asia/Tokyo"


class NewsConfig(BaseModel):
    enabled: bool = True
    feeds: list[str] = Field(default_factory=list)
    max_items_per_feed: int = 10
    lookback_days: int = 7


class Config(BaseModel):
    content: ContentConfig = Field(default_factory=ContentConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    publishers: PublishersConfig = Field(default_factory=PublishersConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    news: NewsConfig = Field(default_factory=NewsConfig)


DEFAULT_CONFIG_PATH = Path("config.yaml")
DEFAULT_ENV_PATH = Path(".env")


def load_config(
    path: Path | str = DEFAULT_CONFIG_PATH,
    env_path: Path | str | None = DEFAULT_ENV_PATH,
) -> Config:
    """Load and validate configuration.

    Reads ``.env`` first (if it exists) so that any code consulting ``os.environ``
    later sees the right values; then parses the YAML config.
    """
    if env_path is not None:
        env_file = Path(env_path)
        if env_file.exists():
            load_dotenv(env_file, override=False)

    config_file = Path(path)
    if not config_file.exists():
        # Fall back to defaults — useful for ``yonkomatic --help`` in fresh checkouts.
        return Config()

    with config_file.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    return Config.model_validate(raw)
