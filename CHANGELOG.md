# Changelog

This project follows Semantic Versioning once it reaches `1.0.0`.

## [Unreleased]

### Security

- Require an explicit, non-trivial HomeKit PIN for every camera; the shared
  `19550224` default is gone.
- Generate a random password for the go2rtc API listener at render time, which
  carries HomeKit pairing data and must not be readable by other LAN devices.
- URL-encode the `ice_servers` fragment in the Kinesis `stream` command.

### Changed

- Decoder ports are keyed to each camera's identity rather than its position in
  `bridge.yaml`, so reordering or inserting cameras no longer repoints existing
  go2rtc streams under preserved HomeKit pairings. An explicit `port` field
  (8099-8114) may be set per camera; ports are allocated automatically when it
  is omitted.
- Wake retries are capped at ten attempts (roughly twenty seconds) and the
  video-track timeout trimmed to match, so a camera tile opens or fails inside
  Apple Home's own patience window instead of hanging.
- `render` regenerates the go2rtc API password on each run; re-render a second
  time only when you also intend to re-pair.

### Fixed

- Live-view requests are locked per camera instead of globally, so a battery
  camera waking slowly can no longer block another camera's stream.
- Concurrent viewers of the same camera can no longer race session replacement
  and leak FFmpeg processes.
- Audio capture batches writes into roughly 100 ms chunks, cutting thread hops
  from about 100 per second per viewer to about 10.
- Removed an unreachable dispatch fallback in the CLI.

## [0.1.0-alpha.4] - 2026-06-23

### Security

- Prevent third-party HTTP exception representations from logging bearer tokens.

### Fixed

- Retry transient HTTP 400/409 responses while waking battery cameras.
- Validate camera UUIDs as exactly 32 hexadecimal characters.
- Render native macOS Docker commands for mixed LiveKit/Kinesis installations.

## [0.1.0-alpha.2] - 2026-06-23

### Added

- Multi-camera LiveKit decoder for current SimpliSafe camera responses.
- Native macOS go2rtc route backed by loopback-only Docker stream ports.
- macOS testing guide for the native go2rtc route.

### Changed

- Current cameras default to the LiveKit transport; Kinesis remains selectable.
- Regenerating go2rtc configuration now preserves HomeKit pairing records.

### Fixed

- Preserve go2rtc's `tini` process supervisor in the camera image.
- Prevent YAML line wrapping from dropping camera IDs from dynamic commands.
- Make the go2rtc HomeKit pairing port reachable from the trusted LAN.

## [0.1.0-alpha.1] - 2026-06-23

### Added

- Docker deployment combining Homebridge and go2rtc.
- OAuth PKCE flow with private, atomic refresh-token storage.
- SimpliSafe location and camera discovery.
- Kinesis live-view conversion for go2rtc.
- Apple Home camera configuration generation.
- UK Video Doorbell Pro route through Homebridge SimpliSafe 3.
- Unit tests, CI, security guidance and repository governance files.
