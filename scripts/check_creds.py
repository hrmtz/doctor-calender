#!/usr/bin/env python3
"""Check credential file path."""
import os

val = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
print(f"raw value: {val}")
print(f"abs path: {os.path.abspath(val)}")
print(f"exists: {os.path.exists(val)}")
print(f"exists(abs): {os.path.exists(os.path.abspath(val))}")
