"""Human-owned Markdown notes and replaceable generated profile snapshots."""

import hashlib
import json
import os
import tempfile
from pathlib import Path


class MemberNotes:
    MAX_BYTES = 32_768

    def __init__(self, root: Path):
        self.root = Path(root)

    def directory(self, persona: str, group: str, user: str) -> Path:
        # IDs are data, never path components. No cross-profile fallback.
        scope = json.dumps([persona, group, user], ensure_ascii=False)
        directory = self.root / hashlib.sha256(scope.encode()).hexdigest()
        if self.root.is_symlink() or directory.is_symlink():
            raise ValueError("Profile notes directory must not be a symlink")
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def read(self, persona: str, group: str, user: str) -> str:
        directory = self.directory(persona, group, user)
        path = directory / "notes.md"
        if path.is_symlink():
            raise ValueError("Member notes must not be a symlink")
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write("")
        except FileExistsError:
            pass
        with path.open("rb") as handle:
            data = handle.read(self.MAX_BYTES + 1)
        if len(data) > self.MAX_BYTES:
            raise ValueError("Member notes exceed 32 KiB")
        return data.decode("utf-8").strip()

    def snapshot(self, persona: str, group: str, user: str, profile: dict) -> None:
        self.read(persona, group, user)  # Creates notes once, never rewrites them.
        directory = self.directory(persona, group, user)
        content = (
            "# Generated observations\n\n"
            "This file is regenerated; edit notes.md for protected human notes.\n"
            "These are model observations, not verified facts.\n\n"
            + "```json\n"
            + json.dumps(
                {
                    "scope": {"persona": persona, "group": group, "user": user},
                    "profile": profile,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n```\n"
        )
        fd, temporary = tempfile.mkstemp(dir=directory, prefix=".observations-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
            os.replace(temporary, directory / "observations.md")
        finally:
            Path(temporary).unlink(missing_ok=True)

    def delete(self, persona: str, group: str, user: str) -> None:
        directory = self.directory(persona, group, user)
        for name in ("notes.md", "observations.md"):
            (directory / name).unlink(missing_ok=True)
        directory.rmdir()
