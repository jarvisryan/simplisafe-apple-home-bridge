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
- Signed Kinesis WebSocket URLs, LiveKit user tokens, ICE servers and TURN credentials.
- HomeKit pairing databases and Docker volume backups.
- Unredacted debug logs, account numbers, addresses and camera serials.

`config/bridge.yaml` contains device identifiers and should normally remain
local. It is ignored by Git.

## Network exposure

The go2rtc API port also carries HomeKit pairing traffic and must be reachable
from Apple devices on the trusted LAN. RTSP remains bound to loopback. The
LiveKit bridge ports are published only on host loopback. Do not publish ports
1984, 8554, 8555, 8581 or 8099-8114 to the internet.

Place the host on a trusted VLAN with outbound HTTPS and local Apple Home access.
Remote viewing should use an Apple home hub, not router port forwarding.

## Security maintenance

- Apply operating-system and Docker security updates promptly.
- Review Dependabot pull requests and image updates before merging.
- Keep repository secret scanning and dependency review enabled.
- Revoke SimpliSafe sessions and reauthenticate if a token may be exposed.
- Rotate each custom HomeKit PIN after an unauthorised pairing.
