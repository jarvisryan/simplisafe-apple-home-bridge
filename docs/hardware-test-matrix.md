# Hardware test matrix

No physical-device result should be marked as passing without the named model,
region, firmware, host architecture and tester date.

| Device | Region | Feature | Status |
| --- | --- | --- | --- |
| Outdoor Camera | UK | Discovery and HomeKit pairing | Passed on macOS arm64, 2026-06-23 |
| Outdoor Camera (LiveKit) | UK | Live video | Passed on macOS arm64, 2026-06-23 |
| Outdoor Camera (Kinesis) | UK | Live video | Passed on macOS arm64, 2026-06-23 |
| Outdoor Camera | UK | Incoming audio | Awaiting hardware validation |
| Outdoor Camera | UK | Motion event in Apple Home | Not implemented |
| Video Doorbell Pro | UK | Homebridge discovery | Upstream-supported; local validation required |
| Video Doorbell Pro | UK | Live video and incoming audio | Upstream-supported; local validation required |
| Video Doorbell Pro | UK | Doorbell event | Upstream-supported; local validation required |
| Wireless Indoor Camera | UK | Live video | Experimental; awaiting hardware validation |

Hardware reports must redact account IDs, addresses, serials, tokens, signed
URLs and ICE credentials before submission.
