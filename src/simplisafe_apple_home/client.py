from __future__ import annotations

from collections.abc import Awaitable
from pathlib import Path
from typing import Any, cast

from aiohttp import ClientSession

from .models import DiscoveredCamera, LiveView
from .storage import TokenStore

WEBRTC_URL_BASE = "https://app-hub.prd.aser.simplisafe.com/v2"


class SimpliSafeClient:
    def __init__(self, api: Any, session: ClientSession, token_store: TokenStore) -> None:
        self._api = api
        self._session = session
        self._token_store = token_store

    @classmethod
    async def create(cls, token_path: Path) -> SimpliSafeClient:
        from simplipy import API  # type: ignore[import-untyped]

        store = TokenStore(token_path)
        session = ClientSession()
        try:
            api = await API.async_from_refresh_token(store.load(), session=session)
        except Exception:
            await session.close()
            raise

        def save_refreshed_token(refresh_token: str) -> Awaitable[None]:
            async def save() -> None:
                store.save(refresh_token)

            return save()

        api.add_refresh_token_callback(save_refreshed_token)
        return cls(api, session, store)

    async def __aenter__(self) -> SimpliSafeClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        await self._session.close()

    async def discover(self) -> list[DiscoveredCamera]:
        systems = await self._api.async_get_systems()
        discovered: list[DiscoveredCamera] = []
        for location_id, system in systems.items():
            cameras = getattr(system, "cameras", {})
            for camera_id, camera in cameras.items():
                features = _read(camera, "camera_supported_features", "cameraSupportedFeatures")
                providers = _read(features, "providers")
                provider = _read(providers, "webrtc")
                discovered.append(
                    DiscoveredCamera(
                        location_id=str(location_id),
                        location_name=str(
                            getattr(system, "address", None)
                            or getattr(system, "name", None)
                            or location_id
                        ),
                        camera_id=str(camera_id),
                        camera_name=str(getattr(camera, "name", None) or camera_id),
                        provider=str(provider) if provider else None,
                        model=_optional_text(
                            _read(camera, "model", "camera_type", "cameraType")
                        ),
                    )
                )
        return discovered

    async def get_live_view(self, location_id: str, camera_id: str) -> LiveView:
        response = await self._api.async_request(
            "get",
            f"cameras/{camera_id}/{location_id}/live-view",
            url_base=WEBRTC_URL_BASE,
        )
        payload = cast(dict[str, Any], response)
        endpoint = payload.get("signedChannelEndpoint")
        client_id = payload.get("clientId")
        ice_servers = payload.get("iceServers")
        if not isinstance(endpoint, str) or not endpoint.startswith("wss://"):
            raise RuntimeError("SimpliSafe returned an invalid Kinesis endpoint")
        if not isinstance(client_id, str) or not client_id:
            raise RuntimeError("SimpliSafe returned an invalid Kinesis client ID")
        if not isinstance(ice_servers, list):
            raise RuntimeError("SimpliSafe returned invalid ICE servers")
        return LiveView(endpoint, client_id, cast(list[dict[str, Any]], ice_servers))


def _optional_text(value: object) -> str | None:
    return str(value) if value is not None else None


def _read(value: object, *names: str) -> object | None:
    for name in names:
        if isinstance(value, dict) and name in value:
            return value[name]
        attribute = getattr(value, name, None)
        if attribute is not None:
            return attribute
    return None
