#!/usr/bin/env python3
"""Validate VERSION and report LV2 minor/micro values."""
import pathlib, re, sys
v = pathlib.Path(__file__).resolve().parents[1].joinpath("VERSION").read_text().strip()
m = re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", v)
if not m:
    sys.exit(f"Invalid VERSION: {v!r}; expected X.Y.Z")
print(f"v{v}: LV2 minorVersion={m.group(2)}, microVersion={m.group(3)}")
