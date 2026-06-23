from typing import Any

from simplisafe_apple_home.livekit_bridge import RuntimeSettings, livekit_credentials


def test_livekit_credentials_reads_valid_response() -> None:
    payload = {
        "cameraStatus": "online",
        "liveKitDetails": {
            "liveKitURL": "wss://livekit.example.test",
            "userToken": "signed-token",
        },
    }

    assert livekit_credentials(payload) == (
        "wss://livekit.example.test",
        "signed-token",
    )


def test_livekit_credentials_rejects_kinesis_response() -> None:
    assert livekit_credentials({"signedChannelEndpoint": "wss://kinesis.test"}) is None


def test_runtime_settings_disable_audio(monkeypatch: Any) -> None:
    monkeypatch.setenv("SSAH_ENABLE_AUDIO", "false")

    assert RuntimeSettings.from_environment().enable_audio is False
