"""What a whole-volume scan must not descend into.

A scan of one project folder needs none of this. A scan of ``/`` needs all of it,
and getting it wrong produces totals that are wrong by a factor of two.
"""

from __future__ import annotations

from pathlib import Path

_BOOT_VOLUME_EXCLUSIONS: tuple[Path, ...] = (
    # Since APFS, macOS mounts the data volume at /System/Volumes/Data and
    # firmlinks /Users, /Applications and friends back into /. A walk of / that
    # also descends here counts the entire disk twice.
    Path("/System/Volumes/Data"),
    # Other disks entirely: external drives, mounted images, network shares.
    # Counting them would answer a question nobody asked.
    Path("/Volumes"),
    # Device nodes rather than files. Their reported sizes are meaningless.
    Path("/dev"),
    # Kernel-managed swap and the sleep image. Large, and not yours to reclaim.
    Path("/private/var/vm"),
)


def boot_volume_exclusions() -> tuple[Path, ...]:
    """Paths a whole-volume scan must skip."""
    return _BOOT_VOLUME_EXCLUSIONS
