#!/usr/bin/env python3
"""Helper script to build and optionally push the setlist-manager Docker image."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys

DEFAULT_VERSION = "1.0.0"
DEFAULT_IMAGE = "registry.124bouchard.com/setlist-manager"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build (and optionally push) the setlist-manager Docker image."
    )
    parser.add_argument(
        "version",
        nargs="?",
        default=DEFAULT_VERSION,
        help=f"Image tag/version (default: {DEFAULT_VERSION})",
    )
    parser.add_argument(
        "--registry",
        default=DEFAULT_IMAGE,
        help=f"Image registry/name (default: {DEFAULT_IMAGE})",
    )
    parser.add_argument(
        "--no-push",
        dest="push",
        action="store_false",
        help="Build the image locally without pushing. Uses docker load.",
    )
    parser.add_argument(
        "--no-update-compose",
        dest="update_compose",
        action="store_false",
        help="Don't update docker-compose.yml after pushing.",
    )
    parser.add_argument(
        "--auto-version",
        action="store_true",
        help="Automatically increment version from docker-compose.yml.",
    )
    parser.set_defaults(push=True, update_compose=True)
    return parser.parse_args()


def ensure_docker_available() -> None:
    if shutil.which("docker") is None:
        print("docker CLI is required but was not found on PATH.", file=sys.stderr)
        sys.exit(1)


def get_current_version_from_compose() -> str:
    """Extract current version from docker-compose.yml."""
    compose_file = "docker-compose.yml"
    if not os.path.exists(compose_file):
        return DEFAULT_VERSION

    try:
        with open(compose_file, 'r') as f:
            content = f.read()
            # Look for image line with version tag
            match = re.search(r'image:\s*.*?:(\d+\.\d+\.\d+)', content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Warning: Could not read docker-compose.yml: {e}", file=sys.stderr)

    return DEFAULT_VERSION


def increment_version(version: str) -> str:
    """Increment the patch version."""
    try:
        major, minor, patch = map(int, version.split('.'))
        patch += 1
        return f"{major}.{minor}.{patch}"
    except ValueError:
        print(f"Warning: Invalid version format '{version}', using default", file=sys.stderr)
        return DEFAULT_VERSION


def update_compose_file(registry: str, version: str) -> None:
    """Update docker-compose.yml with new image tag."""
    compose_file = "docker-compose.yml"
    if not os.path.exists(compose_file):
        print(f"Warning: {compose_file} not found, skipping update", file=sys.stderr)
        return

    try:
        with open(compose_file, 'r') as f:
            content = f.read()

        # Update image tag
        new_content = re.sub(
            r'(image:\s*)[^:]+:\d+\.\d+\.\d+',
            f'\\g<1>{registry}:{version}',
            content
        )

        with open(compose_file, 'w') as f:
            f.write(new_content)

        print(f"Updated {compose_file} with version {version}")
    except Exception as e:
        print(f"Error updating docker-compose.yml: {e}", file=sys.stderr)


def build_image(version: str, registry: str, push: bool) -> None:
    tag = f"{registry}:{version}"
    latest = f"{registry}:latest"

    command = [
        "docker",
        "buildx",
        "build",
        "--platform",
        "linux/amd64",
        "--build-arg",
        "TZ=America/Toronto",
    ]

    command.append("--push" if push else "--load")

    command.extend(
        [
            "-t",
            tag,
            "-t",
            latest,
            ".",
        ]
    )

    subprocess.run(command, check=True)


def main() -> None:
    args = parse_args()
    ensure_docker_available()

    # Handle auto-versioning
    if args.auto_version:
        current_version = get_current_version_from_compose()
        args.version = increment_version(current_version)
        print(f"Auto-incremented version to {args.version}")

    try:
        build_image(args.version, args.registry, args.push)

        # Update docker-compose.yml if requested and push was successful
        if args.push and args.update_compose:
            update_compose_file(args.registry, args.version)

        print(f"Successfully built and pushed {args.registry}:{args.version}")

    except subprocess.CalledProcessError as exc:
        print(f"docker build failed with exit code {exc.returncode}", file=sys.stderr)
        sys.exit(exc.returncode)


if __name__ == "__main__":
    main()
