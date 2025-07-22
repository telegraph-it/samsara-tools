#!/usr/bin/env python3
"""
Entry point for running samsara_tools as a module.
Allows usage: python -m samsara_tools
"""

from .cli.main import main

if __name__ == "__main__":
    main() 