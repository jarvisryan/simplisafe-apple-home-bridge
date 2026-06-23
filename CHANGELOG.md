# Changelog

This project follows Semantic Versioning once it reaches `1.0.0`.

## [Unreleased]

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
