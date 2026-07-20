"""Create one judge bearer key only after an explicit operator authorization flag."""

from __future__ import annotations

import argparse
import hashlib
import os
import secrets
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def validate_destination(destination: Path) -> Path:
    """Require the raw credential destination to remain outside the repository."""
    resolved = destination.expanduser().resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        return resolved
    raise ValueError("credential file must be outside the repository")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a judge credential without printing the raw key.",
    )
    parser.add_argument(
        "--authorize-key-generation",
        action="store_true",
        help="Confirm the operator explicitly authorized judge-key generation.",
    )
    parser.add_argument("--credential-file", required=True, type=Path)
    parser.add_argument("--digest-file", required=True, type=Path)
    arguments = parser.parse_args()
    if not arguments.authorize_key_generation:
        parser.error("--authorize-key-generation is required")

    try:
        destination = validate_destination(arguments.credential_file)
        digest_destination = validate_destination(arguments.digest_file)
        if destination == digest_destination:
            raise ValueError("credential and digest files must be different")
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest_destination.parent.mkdir(parents=True, exist_ok=True)
        key = secrets.token_urlsafe(32)
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(key + "\n")
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        digest_descriptor = os.open(
            digest_destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(digest_descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(digest + "\n")
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(f"Credential written once to: {destination}")
    print(f"Digest written once to: {digest_destination}")
    print("Neither the raw credential nor its full digest was printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
