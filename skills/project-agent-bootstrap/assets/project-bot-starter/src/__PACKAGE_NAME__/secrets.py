"""Resolve secret values from environment variables or a restricted local TXT file."""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


KEY_PATTERN = re.compile(r"[A-Z][A-Z0-9_]{1,127}")


class SecretProviderError(ValueError):
    """Raised when a secret provider is unsafe or incomplete."""


def read_secret_file(path: Path) -> dict[str, str]:
    resolved = path.expanduser().resolve()
    if path.is_symlink() or resolved.is_symlink():
        raise SecretProviderError("secret TXT file must not be a symbolic link")
    if not resolved.is_file():
        raise SecretProviderError("secret TXT file does not exist or is not a regular file")
    if os.name == "posix" and stat.S_IMODE(resolved.stat().st_mode) & 0o077:
        raise SecretProviderError("secret TXT file permissions must be 0600")
    values: dict[str, str] = {}
    for line_number, raw in enumerate(resolved.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise SecretProviderError(f"secret TXT line {line_number} must use KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not KEY_PATTERN.fullmatch(key):
            raise SecretProviderError(f"invalid secret key at line {line_number}")
        if key in values:
            raise SecretProviderError(f"duplicate secret key: {key}")
        if not value or value == "<set-locally>":
            raise SecretProviderError(f"secret key is not set: {key}")
        values[key] = value
    return values


@dataclass(frozen=True)
class SecretResolver:
    mode: str
    values: Mapping[str, str]

    @classmethod
    def from_environment(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        project_root: Path | None = None,
    ) -> "SecretResolver":
        source = os.environ if env is None else env
        mode = source.get("BOT_SECRET_MODE", "env").strip().lower()
        if mode == "env":
            return cls(mode="env", values=source)
        if mode != "file":
            raise SecretProviderError("BOT_SECRET_MODE must be env or file")
        raw_path = source.get("BOT_SECRET_FILE", "./secrets/local-secrets.txt").strip()
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = (project_root or Path.cwd()) / path
        return cls(mode="file", values=read_secret_file(path))

    def get(self, name: str, *, required: bool = True) -> str | None:
        if not KEY_PATTERN.fullmatch(name):
            raise SecretProviderError("secret name must use uppercase KEY syntax")
        value = self.values.get(name)
        if required and not value:
            raise SecretProviderError(f"required secret is not configured: {name}")
        return value

    def public_summary(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "configured_secret_names": sorted(self.values) if self.mode == "file" else [],
            "secret_values_exposed": False,
        }
