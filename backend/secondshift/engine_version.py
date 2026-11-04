"""Engine version + result-cache keys (consistency pass, 2026-11-03).

Bump ENGINE_VERSION whenever anything that can change a report
changes: prompt files, model ids, the keyframe selector, the
verify/sweep logic. The result cache key mixes the version with
the video's sha256 and the pack ids, so a bump cleanly retires
stale answers instead of serving them forever.
"""

import hashlib

ENGINE_VERSION = "2026-11-03.3"


def result_cache_key(
    video_sha256: str,
    pack_ids: list[str],
    verify_mode: str = "sam_plus_judge",
) -> str:
    """One stored report per (video bytes, checklists, engine)."""
    material = "|".join(
        [video_sha256, ",".join(sorted(pack_ids)), ENGINE_VERSION, verify_mode]
    )
    return hashlib.sha256(material.encode()).hexdigest()
