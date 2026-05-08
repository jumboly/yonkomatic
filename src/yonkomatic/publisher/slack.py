"""Slack publisher using slack_sdk.WebClient.files_upload_v2.

Required Slack bot scopes: ``chat:write``, ``files:write``, ``channels:read``.
The bot must also be invited to the target channel.
"""

from __future__ import annotations

from pathlib import Path

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from yonkomatic.publisher.base import Episode, PublishResult


class SlackPublisher:
    name = "slack"

    def __init__(self, token: str, channel: str) -> None:
        self.client = WebClient(token=token)
        self.channel = channel

    def publish(self, episode: Episode, image_path: Path) -> PublishResult:
        title = f"【第{episode.number}話】{episode.title}"
        comment = f"今日の4コマです 🎨\n*あらすじ*: {episode.summary_no_spoiler}"

        try:
            response = self.client.files_upload_v2(
                channel=self.channel,
                file=str(image_path),
                title=title,
                initial_comment=comment,
            )
        except SlackApiError as e:
            return PublishResult(
                ok=False,
                publisher=self.name,
                error=f"SlackApiError: {e.response.get('error', str(e))}",
            )
        except Exception as e:  # network errors, file IO, etc.
            return PublishResult(ok=False, publisher=self.name, error=str(e))

        # files_upload_v2 returns ``files`` list; pull the first entry's metadata.
        files = response.get("files") or []
        first = files[0] if files else {}
        permalink = first.get("permalink")
        file_id = first.get("id")

        return PublishResult(
            ok=True,
            publisher=self.name,
            artifact_id=file_id,
            url=permalink,
        )
