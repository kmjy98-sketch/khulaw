#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEPRECATED: This legacy script is blocked by default.
Use classification_v3.py instead.
"""

import sys


def main() -> int:
    print("[DEPRECATED] This script is blocked.")
    print("Use: python .agent/skills/file-classification/scripts/classification_v3.py --domain legal")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
