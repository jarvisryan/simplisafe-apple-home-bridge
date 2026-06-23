# Security and privacy

## Threat model

The project is intended for a trusted residential LAN. It protects against
accidental credential publication, permissive secret files, unvalidated camera
configuration and unnecessary exposure of management interfaces.

It does not protect a host that is already compromised, a malicious Homebridge
plugin, a hostile LAN administrator, or upstream compromise of SimpliSafe,
Apple, AWS, container images or package registries.

## Sensitive data

The following must never be committed or posted publicly:

- SimpliSafe OAuth redirects, authorisation codes and refresh/access tokens.
- Signed Kinesis WebSocket URLs, ICE servers and TURN credentials.
- HomeKit pairing databases and Docker volume backups.
- Unredacted debug logs, account numbers, addresses and camera serials.

`config/bridge.yaml` contains device identifiers and should normally remain
local. It is ignored by Git.

## Network exposure

Host networking is required for reliable HomeKit discovery. The generated
configuration binds the go2rtc API and RTSP listener to `127.0.0.1`; only its
HomeKit and WebRTC transport listeners are available on the LAN. Do not publish
ports 1984, 8554, 8555 or 8581 to the internet.

Place the host on a trusted VLAN with outbound HTTPS and local Apple Home access.
Remote viewing should use an Apple home hub, not router port forwarding.

## Security maintenance

- Apply operating-system and Docker security updates promptly.
- Review Dependabot pull requests and image updates before merging.
- Keep repository secret scanning and dependency review enabled.
- Revoke SimpliSafe sessions and reauthenticate if a token may be exposed.
- Rotate each custom HomeKit PIN after an unauthorised pairing.

