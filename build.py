#!/usr/bin/env python3
"""Repo-root entrypoint: python build.py --lang en --type 10 --targets pdf"""

from zume_assets.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["build", *(__import__("sys").argv[1:])]))
