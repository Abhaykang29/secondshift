"""live: construct a LiveWatch - the engine's live rule runner.

The watch consumes frames (numpy arrays, e.g. from the phone-camera
hub or any camera source) via process_frame() and emits WatchEvents
through the on_event callback: status changes, alerts, and honest
"can't see" events from the frame health checks.
"""

from collections.abc import Callable

from secondshift.domain.rules import RuleSpec
from secondshift.domain.watch import WatchEvent
from secondshift.providers.registry import Providers
from secondshift.watch.live import LiveWatch


def live(
    spec: RuleSpec,
    source_id: str,
    providers: Providers,
    work_dir: str,
    on_event: Callable[[WatchEvent], None] | None = None,
) -> LiveWatch:
    """Create a LiveWatch for one compiled rule and frame source."""
    return LiveWatch(spec, source_id, providers, work_dir, on_event)
