"""Entry point: python payout.py <tracking|range|all> [--detail|--summary|--json]"""
import sys

from payout_engine.cli import main

sys.exit(main())
