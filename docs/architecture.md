# Architecture

```mermaid
flowchart TD
    SS["SimpliSafe cloud"] --> HB["Homebridge SimpliSafe plugin"]
    SS --> LK["LiveKit room"]
    LK --> LKB["LiveKit decoder"]
    LKB --> G2["go2rtc"]
    SS --> KVS["Kinesis helper"]
    KVS --> G2
    HB --> AH["Apple Home"]
    G2 --> AH
```

Homebridge owns alarm, sensor, lock and Video Doorbell Pro accessories. The
LiveKit decoder requests short-lived room credentials when go2rtc needs a
current Outdoor Camera stream, then supplies local H.264/AAC MPEG-TS. Older
cameras can still request a signed Kinesis WebRTC endpoint directly.

The helper never proxies video through a project-operated server. Video flows
between SimpliSafe/AWS, the local bridge and the user's Apple devices.

## Trust boundaries

| Boundary | Data crossing it | Control |
| --- | --- | --- |
| User to SimpliSafe OAuth | Account login and approval | SimpliSafe-hosted login; password is never handled by this project |
| Bridge to SimpliSafe API | Refresh/access tokens, device metadata | TLS, private token file, minimal calls |
| SimpliSafe KVS to bridge | Camera video and audio | Short-lived signed endpoint and ICE credentials |
| SimpliSafe LiveKit to bridge | Camera video and audio | Short-lived room token; on-demand decoding |
| Bridge to Apple Home | Local HomeKit accessory and media | HomeKit pairing and encrypted local session |

## Failure behaviour

- Invalid authentication stops stream creation and returns a non-zero status.
- Invalid or unsafe configuration prevents go2rtc configuration generation.
- The camera service refuses to start without a generated configuration.
- Alarm monitoring continues independently in the official SimpliSafe system.
