#!/usr/bin/env python3
"""Validate artifacts from reusable workflows; create release ZIPs and notes."""
import argparse
from pathlib import Path
import re
import sys
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("--tag", required=True)
parser.add_argument("--run-number", required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
version = (root / "VERSION").read_text(encoding="utf-8").strip()
if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) or args.tag != f"v{version}":
    sys.exit(f"Refusing release: tag {args.tag!r} does not match VERSION {version!r}")
if not re.fullmatch(r"[0-9]+", args.run_number):
    sys.exit("Invalid run number")

out = root / "release-assets"
out.mkdir(exist_ok=True)
expected = {
    "pistomp-aarch64": "latency_probe.so",
    "windows-x86_64": "latency_probe.dll",
    "linux-x86_64": "latency_probe.so",
}
for platform, binary in expected.items():
    name = f"v{version}-pistomp-midi-latency-probe-{platform}-{args.run_number}"
    stage = root / "downloaded" / name
    bundle = stage / "pistomp-midi-latency-probe.lv2"
    if not bundle.is_dir():
        sys.exit(f"Missing staged LV2 bundle: {bundle}")
    for filename in (binary, "manifest.ttl", "latency_probe.ttl", "modgui.ttl", "LICENSE", "modgui/icon-latency-probe.html",
                      "modgui/stylesheet-latency-probe.css",
                     "modgui/screenshot-latency-probe.png", "modgui/thumbnail-latency-probe.png"):
        if not (bundle / filename).is_file():
            sys.exit(f"Missing {filename} in {name}")
    ttl = (bundle / "latency_probe.ttl").read_text(encoding="utf-8")
    if f'doap:revision "{version}"' not in ttl:
        sys.exit(f"Version mismatch in {name}/latency_probe.ttl")
    if 'https://github.com/tothoseofus/piStomp-MIDI-Latency-Probe' not in ttl:
        sys.exit(f"Unexpected plugin URI in {name}")
    zip_path = out / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for entry in sorted(bundle.rglob("*")):
            if entry.is_file():
                archive.write(entry, entry.relative_to(stage))
    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            sys.exit(f"Invalid ZIP: {zip_path}")
    print(f"Prepared {zip_path.name}")

notes = root / f"RELEASE_NOTES_v{version}.md"
if not notes.is_file():
    sys.exit(f"Missing release notes file: {notes.name}")
content = notes.read_text(encoding="utf-8")
if "NEVER CONNECT" not in content.upper() or "SPEAKER" not in content.upper():
    sys.exit("Refusing release: missing loud PCM safety warning")
(out / "RELEASE_NOTES.md").write_text(content, encoding="utf-8")
print("Prepared release notes")
