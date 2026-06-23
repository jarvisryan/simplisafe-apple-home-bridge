from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from aiohttp import ClientSession

from .storage import PkceStore, TokenStore


@dataclass(frozen=True, slots=True)
class AuthStart:
    url: str


def start_authentication(pkce_store: PkceStore) -> AuthStart:
    from simplipy.util.auth import (  # type: ignore[import-untyped]
        get_auth0_code_challenge,
        get_auth0_code_verifier,
        get_auth_url,
    )

    verifier = get_auth0_code_verifier()
    pkce_store.save(verifier)
    return AuthStart(url=get_auth_url(get_auth0_code_challenge(verifier)))


def extract_authorisation_code(value: str) -> str:
    candidate = value.strip()
    if candidate.lower().startswith("com.simplisafe.mobile://"):
        candidate = parse_qs(urlparse(candidate).query).get("code", [""])[0]
    candidate = candidate.removeprefix("=")
    if len(candidate) < 20 or any(character.isspace() for character in candidate):
        raise ValueError("the SimpliSafe redirect URL or authorisation code is invalid")
    return candidate


async def complete_authentication(
    redirect_or_code: str,
    pkce_store: PkceStore,
    token_store: TokenStore,
) -> None:
    from simplipy import API  # type: ignore[import-untyped]

    verifier = pkce_store.load()
    code = extract_authorisation_code(redirect_or_code)
    async with ClientSession() as session:
        api = await API.async_from_auth(code, verifier, session=session)
        token_store.save(str(api.refresh_token))
    pkce_store.delete()

