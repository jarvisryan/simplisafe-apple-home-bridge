# SimpliSafe Apple Home Bridge

An unofficial, self-hosted bridge for showing supported SimpliSafe equipment in
Apple Home. It combines:

- Homebridge and `homebridge-simplisafe3` for the alarm, sensors, locks,
  SimpliCam and Video Doorbell Pro, including UK systems.
- A small Python helper and `go2rtc` for SimpliSafe Outdoor Cameras that use
  Amazon Kinesis Video Streams (KVS) over WebRTC.

> [!WARNING]
> This project is alpha software. The protocol is undocumented, cloud-dependent
> and can change without notice. Do not rely on it for life safety, alarm
> monitoring or evidential recording. Keep the official SimpliSafe app and
> monitoring service configured.

This project is not affiliated with or endorsed by SimpliSafe or Apple.

## Current support

| Device | Apple Home route | Expected support |
| --- | --- | --- |
| UK Video Doorbell Pro | Homebridge | Live video, incoming audio, motion and doorbell events |
| Outdoor Camera | KVS helper + go2rtc | Live H.264 video and incoming audio |
| Alarm, entry, motion, smoke, CO, water and freeze sensors | Homebridge | Status, alerts and supported controls |
| SimpliSafe Smart Lock | Homebridge | Lock state and control |
| Wireless Indoor Camera | KVS helper + go2rtc | Experimental; hardware testing required |
| Two-way camera audio | Neither | Not currently supported |
| HomeKit Secure Video recording | Neither | Not claimed or supported by this release |

Outdoor Camera wake-up may take several seconds. Battery-powered cameras sleep
between events, and opening them repeatedly in Apple Home can reduce battery
life.

## Requirements

- A Raspberry Pi 4 or newer, an always-on Linux computer, or a compatible NAS.
- Docker Engine with the Compose plugin.
- A SimpliSafe account with access to the relevant cameras.
- An iPhone or iPad on the same local network during pairing.
- An Apple TV or HomePod is recommended for remote Apple Home access.

Linux is the supported host for this alpha. Both containers use host networking
for HomeKit discovery. Docker Desktop host networking and multicast behaviour
vary, so macOS and Windows hosts are not yet supported for production use.

## Quick start

1. Copy the example settings:

   ```sh
   cp .env.example .env
   cp config/bridge.example.yaml config/bridge.yaml
   ```

2. Build the images:

   ```sh
   docker compose build
   ```

3. Start SimpliSafe authentication:

   ```sh
   docker compose run --rm camera-bridge ssah auth start
   ```

   Open the displayed URL on a desktop browser. Complete SimpliSafe sign-in and
   approval. The final redirect begins with `com.simplisafe.mobile://`. Copy the
   complete redirect URL from the browser's developer console.

4. Complete authentication, keeping the redirect URL inside quotes:

   ```sh
   docker compose run --rm camera-bridge ssah auth complete 'com.simplisafe.mobile://...'
   ```

5. Discover camera and location IDs:

   ```sh
   docker compose run --rm camera-bridge ssah discover
   ```

6. Edit `config/bridge.yaml`. Add only Outdoor Cameras that report KVS/WebRTC
   support. Use a different eight-digit `homekit_pin` for each installation.

7. Generate the private go2rtc configuration and start both services:

   ```sh
   docker compose run --rm camera-bridge ssah render
   docker compose up -d
   ```

8. Open Homebridge at `http://HOST-IP:8581`. Configure the already-installed
   **Homebridge SimpliSafe 3** plugin and complete its separate authentication.
   Create a strong Homebridge administrator password during first-run setup.
   Enable cameras for the Video Doorbell Pro. Add each Outdoor Camera serial to
   `excludedDevices` so Homebridge does not create a duplicate, non-working tile.

9. Add Homebridge to Apple Home using the QR code shown in the Homebridge UI.
   Add each Outdoor Camera with **Add Accessory**, **More options**, then its
   configured eight-digit PIN. Apple may warn that the accessory is uncertified;
   this is expected for an unofficial local bridge.

See [Installation](docs/installation.md) for troubleshooting and update steps.

## Security and privacy

- SimpliSafe refresh tokens are stored in a Docker volume, not in the repository
  or Compose environment.
- Token and PKCE files are written atomically with mode `0600`.
- The go2rtc web and RTSP interfaces listen only on loopback by default.
- Containers use `no-new-privileges`.
- Logs do not intentionally print tokens, signed Kinesis URLs or ICE credentials.
- No project-operated cloud service receives account details or video.

Read [Security and privacy](docs/security-and-privacy.md) before installation.
Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

## Development

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
mypy
pytest
```

The test suite mocks SimpliSafe. Hardware validation is tracked separately in
[the test matrix](docs/hardware-test-matrix.md).
Repository owners should also apply the [recommended GitHub settings](docs/github-settings.md).

## Acknowledgements

The Outdoor Camera transport is based on the Kinesis proof of concept from
`gilliginsisland/simplirtc`, released under The Unlicense. Camera delivery uses
the MIT-licensed `AlexxIT/go2rtc`. Alarm, sensor and doorbell integration uses
the MIT-licensed `homebridge-simplisafe3` project. See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Licence

MIT. See [LICENSE](LICENSE).
