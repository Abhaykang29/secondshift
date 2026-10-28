"""Watch room guard (spec sections 9.14 / 12 privacy).

Bathrooms are refused always, in code. Bedrooms require the resident's
explicit consent on the source. Everything else is allowed with consent.
Depends on: domain.watch.
"""

from secondshift.domain.watch import WatchSource

_REFUSED_ROOMS = {"bathroom", "ensuite", "shower_room"}
_CONSENT_ROOMS = {"bedroom"}


class WatchRefused(Exception):
    """Raised when a watch source may not be created or started."""


def assert_watch_allowed(source: WatchSource, room_type: str | None) -> None:
    """Raise WatchRefused if watching this room is not allowed.

    Example: a bathroom source raises with the exact product wording.
    """
    room = (room_type or source.room_type or "").lower()
    if room in _REFUSED_ROOMS or "bathroom" in room:
        raise WatchRefused("I can't watch in a bathroom. Bathrooms are always private.")
    if room in _CONSENT_ROOMS and not source.resident_consent:
        raise WatchRefused("A bedroom watch needs the resident's own consent first.")
