#!/usr/bin/env python3
"""Disable Supabase env keys on EC2 for AWS-only auth + SQLite."""
from __future__ import annotations

import shutil
import time
from pathlib import Path

BACKEND = Path("/home/ubuntu/srivatsanka/whatsapp/.env")
WEBSITE = Path("/home/ubuntu/srivatsanka/website/.env")
BACKEND_KEYS = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_JWT_SECRET")
WEBSITE_KEYS = ("VITE_SUPABASE_URL", "VITE_SUPABASE_ANON_KEY")


def strip_keys(path: Path, keys: tuple[str, ...]) -> None:
    if not path.exists():
        print(f"skip missing {path}")
        return
    stamp = time.strftime("%Y%m%d%H%M%S")
    backup = path.with_name(path.name + f".bak-supabase-{stamp}")
    shutil.copy2(path, backup)
    print(f"backup {backup}")
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines(True):
        stripped = line.lstrip()
        hit = False
        for key in keys:
            if stripped.startswith(f"{key}=") and not stripped.startswith("#"):
                out.append(f"# AWS-only disabled: {line if line.endswith(chr(10)) else line + chr(10)}")
                hit = True
                break
        if not hit:
            out.append(line if line.endswith("\n") else line + "\n")
    path.write_text("".join(out), encoding="utf-8")
    print(f"updated {path}")


def main() -> None:
    strip_keys(BACKEND, BACKEND_KEYS)
    strip_keys(WEBSITE, WEBSITE_KEYS)
    print("done")


if __name__ == "__main__":
    main()
