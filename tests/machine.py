"""Builds a temp tree that looks like a real developer's Mac.

Tests run against this rather than two-file toys. The scanner's job is to stay
correct on a machine where an active project, stale build output, package caches,
a locked directory and a symlink are all present at once — and that interaction
is the only place the interesting bugs live.

Sizes are kept small; the *shape* is what makes the fixture realistic, not the
gigabytes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

KB = 1024

FILES: dict[str, int] = {
    # A project you're actively working on.
    "Sites/client-app/package.json": 2 * KB,
    "Sites/client-app/src/main.ts": 6 * KB,
    "Sites/client-app/node_modules/react/index.js": 300 * KB,
    "Sites/client-app/node_modules/lodash/index.js": 700 * KB,
    "Sites/client-app/node_modules/.bin/tsc": 40 * KB,
    # No manifest beside it, so no rule claims it: this is what a genuinely
    # opaque directory looks like, and it is what the model gets asked about.
    "Sites/client-app/mockups/home-v3.png": 180 * KB,
    # An older one, with a Cargo.toml sitting beside its target/ directory.
    "Sites/old-project/Cargo.toml": 1 * KB,
    "Sites/old-project/src/lib.rs": 12 * KB,
    "Sites/old-project/target/debug/app": 900 * KB,
    "Sites/old-project/target/debug/deps/core.rlib": 450 * KB,
    # Where macOS actually hides space.
    "Library/Caches/com.apple.Safari/cache.db": 250 * KB,
    # A recognised directory nested inside another recognised directory: the pip
    # cache has its own rule, and it lives inside ~/Library/Caches which also has
    # one. Counting both would report the same bytes twice.
    "Library/Caches/pip/http/ab/cd/blob": 310 * KB,
    "Library/Developer/Xcode/DerivedData/App-abc/Build/app.o": 800 * KB,
    "Library/Developer/Xcode/DerivedData/App-abc/Index/index.db": 200 * KB,
    # Genuinely ambiguous: a shipped release cannot be rebuilt, but old ones are
    # dead weight. The catalog calls this `review` rather than guessing.
    "Library/Developer/Xcode/Archives/2024-11-14/App.xcarchive/Info.plist": 430 * KB,
    ".npm/_cacache/content-v2/sha512/ab/cd/blob": 380 * KB,
    # Credentials: never-delete whatever they contain.
    ".ssh/id_ed25519": 1 * KB,
    ".ssh/known_hosts": 3 * KB,
    # Things you would hate to lose.
    "Documents/contract-signed.pdf": 90 * KB,
    "Archive/clients-2021/final-delivery.zip": 640 * KB,
    # Downloads, shaped after a real one: 8.6 GB over 124 files, where two files
    # were 97% of it and 93 PDFs were noise. The long tail is not the problem.
    "Downloads/screen-recording-2024-11-14.mp4": 5200 * KB,
    "Downloads/dataset-export.zip": 3100 * KB,
    "Downloads/installer.dmg": 520 * KB,
    "Downloads/invoice-2024-01.pdf": 3 * KB,
    "Downloads/invoice-2024-02.pdf": 3 * KB,
    "Downloads/invoice-2024-03.pdf": 4 * KB,
    "Downloads/notes.txt": 4 * KB,
}

LOCKED = "Library/Application Support/locked"
"""Made unreadable. Its contents must never reach the total."""

LOCKED_CONTENTS = 999 * KB

SYMLINK = "shortcut-to-app"
SYMLINK_TARGET = "Sites/client-app"


@dataclass(frozen=True)
class Machine:
    root: Path

    @property
    def readable_bytes(self) -> int:
        """Everything the scanner should be able to see and count, exactly once."""
        return sum(FILES.values())

    def path(self, relpath: str) -> Path:
        return self.root / relpath


def _filler(relpath: str, size: int) -> bytes:
    """Distinct bytes per file, deterministically.

    Writing zeros everywhere would make any two files of equal size genuinely
    byte-identical, so duplicate detection would find pairs the fixture never
    meant to create. Real files differ; so do these.
    """
    seed = relpath.encode()
    return (seed * (size // len(seed) + 1))[:size]


def build(root: Path) -> Machine:
    for relpath, size in FILES.items():
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_filler(relpath, size))

    locked = root / LOCKED
    locked.mkdir(parents=True, exist_ok=True)
    (locked / "secret.bin").write_bytes(b"\0" * LOCKED_CONTENTS)
    locked.chmod(0o000)

    (root / SYMLINK).symlink_to(root / SYMLINK_TARGET)

    return Machine(root=root)


def unlock(root: Path) -> None:
    """Restore permissions so temp cleanup can't fail."""
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_dir() and not path.is_symlink():
            path.chmod(0o755)


def running_as_root() -> bool:
    """Root bypasses directory permissions, so the locked directory wouldn't lock."""
    return os.geteuid() == 0
