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

ImageSize = Literal["512", "1K", "2K", "4K"]
AspectRatio = Literal["1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9", "21:9"]
TextRenderMode = Literal["pil_overlay", "model_render"]
BubbleStyle = Literal["round", "rectangle", "cloud"]


class ContentConfig(BaseModel):
    base_dir: Path = Path("./content")
    characters_dir: str = "characters"
    world_dir: str = "world"
    samples_dir: str = "samples"
    themes_dir: str = "themes"

    def characters_path(self, base: Path | None = None) -> Path:
        return (base or self.base_dir) / self.characters_dir

    def world_path(self, base: Path | None = None) -> Path:
        return (base or self.base_dir) / self.world_dir

    def samples_path(self, base: Path | None = None) -> Path:
        return (base or self.base_dir) / self.samples_dir

    def themes_path(self, base: Path | None = None) -> Path:
        return (base or self.base_dir) / self.themes_dir


class AIConfig(BaseModel):
    scenario_model: str = "claude-sonnet-4-6"
    image_model: str = "gemini-3.1-flash-image-preview"
    image_size: ImageSize = "1K"
    aspect_ratio: AspectRatio = "3:4"
    max_image_retries: int = 3
    scenario_api_key_env: str = "ANTHROPIC_API_KEY"
    image_api_key_env: str = "GOOGLE_AI_STUDIO_API_KEY"


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
    publish_time: str = "09:00"
    scenario_generation_dow: str = "sunday"
    scenario_generation_time: str = "23:00"


class NewsConfig(BaseModel):
    enabled: bool = True
    feeds: list[str] = Field(default_factory=list)
    max_items_per_feed: int = 10
    lookback_days: int = 7
    language: str = "ja"


class TextRenderingConfig(BaseModel):
    # Why "pil_overlay" default: lower-tier Gemini image models hallucinate
    # Japanese characters when asked to render multiple bubbles, so we
    # instruct Gemini to skip text and composite Japanese with PIL afterwards.
    # "model_render" lets the image model draw bubbles + text directly
    # (skips PIL); only viable on higher-tier models that can render
    # legible Japanese reliably (e.g. gemini-3-pro-image-preview).
    mode: TextRenderMode = "pil_overlay"
    font_path: Path = Path("./assets/fonts/NotoSansJP-Regular.otf")
    bubble_style: BubbleStyle = "round"


class Config(BaseModel):
    content: ContentConfig = Field(default_factory=ContentConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    publishers: PublishersConfig = Field(default_factory=PublishersConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    news: NewsConfig = Field(default_factory=NewsConfig)
    text_rendering: TextRenderingConfig = Field(default_factory=TextRenderingConfig)


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
