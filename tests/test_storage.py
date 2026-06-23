import json
import os
from pathlib import Path

import pytest

from simplisafe_apple_home.storage import SecretFileError, TokenStore


def test_round_trip_uses_private_permissions(tmp_path: Path) -> None:
    path = tmp_path / "token.json"
    store = TokenStore(path)
    store.save("x" * 32)

    assert store.load() == "x" * 32
    assert path.stat().st_mode & 0o777 == 0o600
    assert json.loads(path.read_text())["version"] == 1


def test_rejects_world_readable_secret(tmp_path: Path) -> None:
    path = tmp_path / "token.json"
    path.write_text(json.dumps({"refresh_token": "x" * 32}))
    os.chmod(path, 0o644)

    with pytest.raises(SecretFileError, match="permissions"):
        TokenStore(path).load()


def test_reads_legacy_string_token(tmp_path: Path) -> None:
    path = tmp_path / "token.json"
    path.write_text(json.dumps("x" * 32))
    os.chmod(path, 0o600)
    assert TokenStore(path).load() == "x" * 32

