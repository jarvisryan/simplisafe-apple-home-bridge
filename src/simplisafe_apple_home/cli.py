from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .auth import complete_authentication, start_authentication
from .client import SimpliSafeClient
from .go2rtc import live_view_uri, write_go2rtc_config
from .models import BridgeConfig
from .storage import PkceStore, TokenStore

DEFAULT_TOKEN = Path("/data/simplisafe-token.json")
DEFAULT_PKCE = Path("/data/simplisafe-pkce.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ssah", description="Configure SimpliSafe cameras for Apple Home"
    )
    parser.add_argument("--token", type=Path, default=DEFAULT_TOKEN, help="refresh-token file")
    commands = parser.add_subparsers(dest="command", required=True)

    auth = commands.add_parser("auth", help="authenticate with SimpliSafe")
    auth_commands = auth.add_subparsers(dest="auth_command", required=True)
    auth_start = auth_commands.add_parser("start", help="start OAuth authentication")
    auth_start.add_argument("--pkce", type=Path, default=DEFAULT_PKCE)
    auth_complete = auth_commands.add_parser("complete", help="complete OAuth authentication")
    auth_complete.add_argument("redirect", help="redirect URL or authorisation code")
    auth_complete.add_argument("--pkce", type=Path, default=DEFAULT_PKCE)

    commands.add_parser("discover", help="list SimpliSafe locations and cameras")

    stream = commands.add_parser("stream", help="print a short-lived go2rtc Kinesis URI")
    stream.add_argument("--location", required=True)
    stream.add_argument("--camera", required=True)

    render = commands.add_parser("render", help="render go2rtc.yaml from bridge.yaml")
    render.add_argument("--config", type=Path, default=Path("/config/bridge.yaml"))
    render.add_argument("--output", type=Path, default=Path("/config/go2rtc.yaml"))
    return parser


async def run(args: argparse.Namespace) -> int:
    token_store = TokenStore(args.token)
    if args.command == "auth" and args.auth_command == "start":
        result = start_authentication(PkceStore(args.pkce))
        print(result.url)
        return 0
    if args.command == "auth" and args.auth_command == "complete":
        await complete_authentication(args.redirect, PkceStore(args.pkce), token_store)
        print("Authentication completed. The refresh token is stored in the private data volume.")
        return 0
    if args.command == "render":
        write_go2rtc_config(BridgeConfig.load(args.config), args.output, args.token)
        print(f"Wrote {args.output}")
        return 0

    async with await SimpliSafeClient.create(args.token) as client:
        if args.command == "discover":
            print(json.dumps([camera.as_dict() for camera in await client.discover()], indent=2))
            return 0
        if args.command == "stream":
            print(live_view_uri(await client.get_live_view(args.location, args.camera)))
            return 0
    return 2


def main() -> int:
    try:
        return asyncio.run(run(build_parser().parse_args()))
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
