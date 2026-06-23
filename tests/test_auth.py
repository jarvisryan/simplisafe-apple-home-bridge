import pytest

from simplisafe_apple_home.auth import extract_authorisation_code


def test_extracts_code_from_redirect_url() -> None:
    code = "a" * 45
    assert extract_authorisation_code(f"com.simplisafe.mobile://auth?code={code}") == code


def test_accepts_plain_code() -> None:
    code = "b" * 45
    assert extract_authorisation_code(code) == code


@pytest.mark.parametrize("value", ["", "short", "contains spaces and is invalid"])
def test_rejects_invalid_code(value: str) -> None:
    with pytest.raises(ValueError, match="invalid"):
        extract_authorisation_code(value)

