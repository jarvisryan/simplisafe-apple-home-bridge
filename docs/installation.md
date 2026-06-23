# Installation

## Host preparation

Use a supported 64-bit Linux host with a fixed DHCP reservation. Confirm that
Docker and Compose work:

```sh
docker version
docker compose version
```

The host, Apple devices and SimpliSafe cameras should be on the same trusted
home network. Client isolation and blocked multicast DNS can prevent pairing.

## Authentication

The camera bridge and Homebridge plugin each maintain their own OAuth refresh
token. This avoids sharing private implementation details between projects.

The camera token is held in the `camera-secrets` Docker volume. Never paste a
redirect URL, authorisation code, refresh token, signed Kinesis URL or full debug
log into a public GitHub issue.

If authentication fails, remove only the incomplete PKCE file and start again:

```sh
docker compose run --rm camera-bridge sh -c 'rm -f /data/simplisafe-pkce.json'
```

Do not remove the `camera-secrets` volume unless you intend to authenticate
again.

## Camera configuration

`ssah discover` returns location and camera IDs. A typical configuration is:

```yaml
cameras:
  - name: Back Garden
    location_id: "1234567"
    camera_id: "abcdef0123456789"
    homekit_pin: "48276135"
    preload: false
```

Keep `preload: false` for battery-powered Outdoor Cameras. Preloading can improve
the first-frame delay but may substantially increase power use.

After changing the file, regenerate and restart:

```sh
docker compose run --rm camera-bridge ssah render
docker compose restart camera-bridge
```

## Doorbell Pro and sensors

Open Homebridge at `http://HOST-IP:8581`, configure Homebridge SimpliSafe 3 and
authenticate. Recommended settings:

| Setting | Value |
| --- | --- |
| Cameras | Enabled |
| Sensor refresh | 15 seconds or slower |
| Persist accessories | Enabled |
| Excluded devices | Every Outdoor Camera serial configured in `bridge.yaml` |

Do not poll sensors more frequently than the plugin default. Excessive cloud API
requests can trigger temporary rate limiting.

## Updates

Back up pairing and configuration data first:

```sh
docker run --rm -v simplisafe-apple-home_homebridge-data:/source -v "$PWD":/backup alpine \
  tar -czf /backup/homebridge-data.tgz -C /source .
docker run --rm -v simplisafe-apple-home_camera-secrets:/source -v "$PWD":/backup alpine \
  tar -czf /backup/camera-secrets.tgz -C /source .
```

Then rebuild:

```sh
git pull --ff-only
docker compose build --pull
docker compose up -d
```

Review `CHANGELOG.md` before updating. Do not publish backup archives; they
contain credentials and HomeKit pairing material.

## Troubleshooting

### Camera does not appear

- Confirm `config/go2rtc.yaml` exists and the camera bridge is running.
- Confirm the camera ID and location ID were copied exactly.
- Confirm the camera reports a KVS/WebRTC provider.
- Check that multicast DNS works between the host and iPhone.

### Camera says No Response

- Open the camera once in the official SimpliSafe app to confirm it is online.
- Wait up to 15 seconds for a sleeping Outdoor Camera to wake.
- Move the camera closer to its base station or Wi-Fi access point for testing.
- Check redacted logs with `docker compose logs camera-bridge`.

### Doorbell tile is missing

- Confirm cameras are enabled in Homebridge SimpliSafe 3.
- Do not add the Doorbell Pro serial to `excludedDevices`.
- Restart the Homebridge child bridge after changing plugin settings.

