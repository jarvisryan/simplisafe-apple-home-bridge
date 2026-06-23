from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any


class SecretFileError(RuntimeError):
    """Raised when a secret file is missing or has unsafe permissions."""


class TokenStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> str:
        try:
            mode = stat.S_IMODE(self.path.stat().st_mode)
        except FileNotFoundError as error:
            raise SecretFileError(f"token file does not exist: {self.path}") from error

        if mode & 0o077:
            raise SecretFileError(
                f"token file permissions are too broad ({mode:o}); run chmod 600 {self.path}"
            )

        payload: Any = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(payload, str):
            return payload
        if not isinstance(payload, dict) or not isinstance(payload.get("refresh_token"), str):
            raise SecretFileError("token file has an invalid format")
        return payload["refresh_token"]

    def save(self, refresh_token: str) -> None:
        if not refresh_token or len(refresh_token) < 20:
            raise SecretFileError("refusing to store an invalid refresh token")

        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        payload = json.dumps({"version": 1, "refresh_token": refresh_token}) + "\n"

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=self.path.parent, text=True
        )
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            temporary_path.replace(self.path)
        finally:
            temporary_path.unlink(missing_ok=True)


class PkceStore:
    def __init__(self, path: Path) -> None:
        self._store = TokenStore(path)

    def load(self) -> str:
        return self._store.load()

    def save(self, verifier: str) -> None:
        self._store.save(verifier)

    def delete(self) -> None:
        self._store.path.unlink(missing_ok=True)

