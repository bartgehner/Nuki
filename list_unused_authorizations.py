#!/usr/bin/env python3
"""
List Nuki smartlock authorizations that have never been used (lockCount == 0).

Usage:
    export NUKI_API_TOKEN=xxxxxxxx
    python3 list_unused_authorizations.py [--include-bridge] [--csv out.csv]

Get a token at web.nuki.io -> Account -> API ("API Token"), used as a
Bearer token. No OAuth dance needed for a personal script like this.
"""
import argparse
import csv
import os
import sys

import requests

API_BASE = "https://api.nuki.io"

AUTH_TYPE_NAMES = {
    0: "app",
    1: "bridge",
    2: "fob",
    3: "keypad",
    13: "keypad code",
    14: "z-key",
    15: "virtual",
}


def api_get(path: str, token: str, **params):
    resp = requests.get(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--token",
        default=os.environ.get("NUKI_API_TOKEN"),
        help="Nuki API bearer token (default: NUKI_API_TOKEN env var)",
    )
    parser.add_argument(
        "--include-bridge",
        action="store_true",
        help="Also include bridge authorizations (excluded by default, since a bridge isn't a 'user')",
    )
    parser.add_argument("--csv", help="Write results to this CSV file")
    args = parser.parse_args()

    if not args.token:
        sys.exit("Error: no API token. Pass --token or set NUKI_API_TOKEN.")

    smartlocks = api_get("/smartlock", args.token)

    unused = []
    for lock in smartlocks:
        lock_id = lock["smartlockId"]
        lock_name = lock.get("name", f"smartlock {lock_id}")
        auths = api_get(f"/smartlock/{lock_id}/auth", args.token)

        for auth in auths:
            if auth.get("type") == 1 and not args.include_bridge:
                continue
            if auth.get("lockCount", 0) == 0:
                unused.append(
                    {
                        "smartlock": lock_name,
                        "smartlockId": lock_id,
                        "authName": auth.get("name", ""),
                        "authId": auth.get("id", ""),
                        "type": AUTH_TYPE_NAMES.get(auth.get("type"), auth.get("type")),
                        "enabled": auth.get("enabled"),
                        "creationDate": auth.get("creationDate", ""),
                        "lastActiveDate": auth.get("lastActiveDate", ""),
                    }
                )

    if not unused:
        print("No unused authorizations found.")
        return

    header = ["smartlock", "authName", "type", "enabled", "creationDate", "lastActiveDate", "authId", "smartlockId"]
    widths = {h: max(len(h), *(len(str(row[h])) for row in unused)) for h in header}
    print("  ".join(h.ljust(widths[h]) for h in header))
    for row in unused:
        print("  ".join(str(row[h]).ljust(widths[h]) for h in header))

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            for row in unused:
                writer.writerow({h: row[h] for h in header})
        print(f"\nWrote {len(unused)} rows to {args.csv}")


if __name__ == "__main__":
    main()
