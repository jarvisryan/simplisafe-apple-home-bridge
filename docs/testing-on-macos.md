# Testing on macOS

Docker Desktop cannot reliably advertise HomeKit multicast services onto the
Mac's LAN. Run the LiveKit decoder in Docker and go2rtc natively on macOS.

The Mac and the iPhone or iPad used for pairing must be on the same trusted
network. Keep Docker Desktop running and prevent the Mac from sleeping.

## Prepare and authenticate

```sh
cp .env.example .env
cp config/bridge.example.yaml config/bridge.yaml
docker compose build camera-bridge livekit-bridge
docker compose run --rm camera-bridge ssah auth start
docker compose run --rm camera-bridge ssah auth complete 'PASTE-REDIRECT-URL-HERE'
docker compose run --rm camera-bridge ssah discover
```

Do not share the redirect URL, camera IDs, token files or signed stream data.
Add the desired cameras to `config/bridge.yaml` with `transport: livekit`.

## Install native go2rtc

For an Apple Silicon Mac:

```sh
mkdir -p bin
curl -L "https://github.com/AlexxIT/go2rtc/releases/download/v1.9.14/go2rtc_mac_arm64.zip" \
  -o bin/go2rtc_mac_arm64.zip
unzip -o bin/go2rtc_mac_arm64.zip -d bin
chmod +x bin/go2rtc
xattr -d com.apple.quarantine bin/go2rtc 2>/dev/null || true
```

Intel Mac users must download `go2rtc_mac_amd64.zip` instead.

## Render and run

The renderer preserves existing HomeKit pairing records when the output file
already exists.

```sh
docker compose run --rm camera-bridge ssah render \
  --output /config/go2rtc-mac.yaml \
  --native-compose "$PWD/compose.yaml"
docker compose up -d livekit-bridge
./bin/go2rtc -config config/go2rtc-mac.yaml
```

Leave go2rtc running. If macOS asks about incoming connections, select
**Allow**. Add each camera from Apple Home using its PIN from `bridge.yaml`.

The first view can take up to one minute while a battery camera wakes. The
decoder is on demand and returns to idle when viewing stops.

## Troubleshooting

Confirm the decoder is listening:

```sh
docker compose logs --tail=100 livekit-bridge
```

Confirm HomeKit advertisements locally:

```sh
dns-sd -B _hap._tcp local.
```

The go2rtc page should open from the iPhone at `http://MAC-IP:1984`. Never
forward that port from the router.

## Stop the test

Press `Control+C` in the go2rtc Terminal, then run:

```sh
docker compose stop livekit-bridge
```
