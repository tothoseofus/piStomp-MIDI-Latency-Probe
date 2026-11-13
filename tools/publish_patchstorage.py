#!/usr/bin/env python3
"""Publish a GitHub MIDI Latency Probe release through Patchstorage's LV2 uploader.

Only the rpi-aarch64 and linux-amd64 targets are published. The upstream
uploader prepares tar.gz archives; no changes are made to GitHub ZIPs or TTL.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import zipfile

PLUGIN_DIR = "pistomp-midi-latency-probe.lv2"
PLUGIN_URI = "https://github.com/tothoseofus/piStomp-MIDI-Latency-Probe"
SOURCE_URL = PLUGIN_URI
PLATFORMS = {"pistomp-aarch64": "rpi-aarch64", "linux-x86_64": "linux-amd64"}


def version_tuple(value: str) -> tuple[int, int, int]:
    """Strict semantic release versions for downgrade prevention."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(value)):
        raise RuntimeError(f"Cannot compare Patchstorage revision: {value!r}")
    return tuple(map(int, value.split(".")))


def stage_zip(zip_path: Path, target_dir: Path, version: str, platform: str) -> None:
    target_dir.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError(f"Corrupt ZIP: {zip_path}")
        for info in archive.infolist():
            path = Path(info.filename)
            if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != PLUGIN_DIR:
                raise RuntimeError(f"Unexpected path in {zip_path}: {info.filename}")
        for info in archive.infolist():
            dest = target_dir.joinpath(*Path(info.filename).parts)
            if info.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, dest.open("wb") as dst:
                    import shutil
                    shutil.copyfileobj(src, dst)
    bundle = target_dir / PLUGIN_DIR
    binary = bundle / "latency_probe.so"
    if not binary.is_file():
        raise RuntimeError(f"Missing {binary}")
    ttl = (bundle / "latency_probe.ttl").read_text(encoding="utf-8")
    if f'doap:revision "{version}"' not in ttl or f"<{PLUGIN_URI}>" not in ttl:
        raise RuntimeError(f"Version or plugin URI mismatch in {zip_path}")
    if "DO NOT CONNECT" not in ttl.upper():
        raise RuntimeError("Missing speaker safety warning in metadata")
    if not (bundle / "modgui/screenshot-latency-probe.png").is_file():
        raise RuntimeError(f"Missing screenshot in {zip_path}")
    print(f"Staged {platform}: {zip_path.name}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tag", required=True)
    p.add_argument("--release-dir", type=Path, required=True)
    p.add_argument("--uploader-dir", type=Path, required=True)
    args = p.parse_args()
    if not re.fullmatch(r"v\d+\.\d+\.\d+", args.tag):
        raise RuntimeError("Expected tag vMAJOR.MINOR.PATCH")
    version = args.tag[1:]
    uploader_dir = args.uploader_dir.resolve()
    if not (uploader_dir / "uploader.py").is_file():
        raise RuntimeError("Missing upstream Patchstorage uploader")

    for platform, slug in PLATFORMS.items():
        glob = f"{args.tag}-pistomp-midi-latency-probe-{platform}-*.zip"
        matches = list(args.release_dir.glob(glob))
        if len(matches) != 1:
            raise RuntimeError(f"Expected one {platform} asset, found {len(matches)}: {glob}")
        stage_zip(matches[0], uploader_dir / "plugins" / slug, version, platform)

    # Upstream uploader needs a per-plugin source URL and donate key.
    overrides_path = uploader_dir / "plugins.json"
    overrides = json.loads(overrides_path.read_text(encoding="utf-8"))
    overrides[PLUGIN_DIR] = {"source_code_url": SOURCE_URL, "donate_url": None}
    overrides_path.write_text(json.dumps(overrides, indent=2) + "\n", encoding="utf-8")

    # GPL-3.0-only must not be misidentified as GPL-3.0-or-later.
    # Resolve its Patchstorage licence ID from the uploader's mapping.
    license_path = uploader_dir / "licenses.json"
    licenses = json.loads(license_path.read_text(encoding="utf-8"))
    candidates = {
        "https://www.gnu.org/licenses/gpl-3.0.html",
        "https://spdx.org/licenses/GPL-3.0-only.html",
        "https://opensource.org/license/gpl-3-0",
    }
    found = [key for key, aliases in licenses.items()
             if isinstance(aliases, list) and candidates.intersection(aliases)]
    if len(found) != 1:
        raise RuntimeError(
            "Patchstorage uploader has no unambiguous GPL-3.0-only mapping. "
            "Inspect licenses.json and correct the alias rather than "
            "publishing with GPL-3.0-or-later.")
    # Make sure our actual declared doap:license URI is recognised.
    aliases = licenses[found[0]]
    if "https://www.gnu.org/licenses/gpl-3.0.html" not in aliases:
        aliases.append("https://www.gnu.org/licenses/gpl-3.0.html")
    license_path.write_text(json.dumps(licenses, indent=2) + "\n", encoding="utf-8")

    # Import upstream uploader as a library so upload errors fail the workflow
    # (the upstream `push all` CLI catches some errors and continues).
    sys.path.insert(0, str(uploader_dir))
    from uploader import PluginManager, Patchstorage  # pylint: disable=import-error,import-outside-toplevel

    os.chdir(uploader_dir)
    manager = PluginManager()
    manager.scan_plugins_directory()
    manager.do_cleanup(manager.dist_path)
    multi = manager.get_multi_bundle(PLUGIN_DIR)
    if len(multi.bundles) != 2:
        raise RuntimeError(f"Expected 2 Patchstorage targets, got {len(multi.bundles)}")
    # This raises on unsupported metadata rather than silently skipping the bundle.
    manager._prepare_bundle(multi)
    metadata_path = manager.dist_path / PLUGIN_DIR / "patchstorage.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if len(metadata["files"]) != 2 or metadata["uids"] != [PLUGIN_URI]:
        raise RuntimeError("Unexpected Patchstorage metadata")
    # Use the GitHub tag as the canonical version, not the LV2 minor/micro values.
    metadata["revision"] = version
    metadata["content"] = (
        "SAFETY WARNING: NEVER connect the Encoded MIDI Right output to "
        "speakers, amplifiers, headphones or any audio monitoring device. "
        "Diagnostic PCM pulses only; record with monitoring muted.\n\n"
        "piStomp MIDI Latency Probe captures original guitar audio on its "
        "left output and timestamp-encoded MIDI messages on its right output "
        "for offline latency analysis.\n\n"
        "This Patchstorage listing provides Raspberry Pi ARM64 and Linux x64 "
        "builds. A Windows build for MOD Desktop is available on GitHub.\n\n"
        "Source, documentation, releases and full changelog: " + SOURCE_URL +
        "\n\nMaintainer: Ken Spanks"
    )
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    username = os.environ.get("PATCHSTORAGE_USERNAME", "").strip()
    password = os.environ.get("PATCHSTORAGE_PASSWORD", "")
    if not username or not password:
        raise RuntimeError("PATCHSTORAGE_USERNAME and PATCHSTORAGE_PASSWORD secrets are required")
    auth = Patchstorage.auth(username, password)
    existing = Patchstorage.get(uids=[PLUGIN_URI])
    if existing is not None:
        owner = existing.get("author", {}).get("slug", "").lower()
        accepted = {username.lower(), str(auth.get("display_name", "")).lower()}
        if owner not in accepted:
            raise RuntimeError(f"Patchstorage entry belongs to another user: {owner}")
        remote_version = str(existing.get("revision", ""))
        if version_tuple(remote_version) > version_tuple(version):
            raise RuntimeError(
                f"Refusing downgrade: Patchstorage {remote_version} is newer than {version}"
            )
        if remote_version == version:
            if len(existing.get("files", [])) == 2:
                print(f"Already published: {existing.get('url')} ({version}); skipping")
                return
            print("Same release revision but missing target files; updating")
        result = Patchstorage.update(PLUGIN_DIR, metadata, existing["id"])
    else:
        result = Patchstorage.upload(PLUGIN_DIR, metadata)
    if not result.get("url"):
        raise RuntimeError(f"Patchstorage API did not confirm publication: {result}")
    print(f"Published to Patchstorage: {result['url']}")


if __name__ == "__main__":
    main()
