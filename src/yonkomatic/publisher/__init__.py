"""Publisher Protocol and concrete implementations.

The Publisher abstraction lets yonkomatic post the same Episode to many
platforms (Slack, Discord, static site, ...) with a uniform interface.
Each Publisher returns a PublishResult; failures of one Publisher must
not break the others — the daily pipeline records each result and keeps
going.
"""

from yonkomatic.publisher.base import Episode, Publisher, PublishResult

__all__ = ["Episode", "Publisher", "PublishResult"]
