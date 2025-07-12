#!/usr/bin/env python3
"""
Script to set up Virtuoso provenance database for Heritrace end-user testing.
"""

import argparse
import sys

from virtuoso_utils import (
    DEFAULT_VIRTUOSO_HOST,
    DEFAULT_VIRTUOSO_PORT,
    DEFAULT_VIRTUOSO_USER,
    DEFAULT_VIRTUOSO_PASSWORD,
    wait_for_virtuoso,
    setup_fulltext_indexing,
    set_permissions
)

def main():
    parser = argparse.ArgumentParser(description="Set up Virtuoso provenance database for Heritrace")
    parser.add_argument("-H", "--host", default=DEFAULT_VIRTUOSO_HOST, help=f"Virtuoso host (default: {DEFAULT_VIRTUOSO_HOST})")
    parser.add_argument("-P", "--port", type=int, default=DEFAULT_VIRTUOSO_PORT, help=f"Virtuoso port (default: {DEFAULT_VIRTUOSO_PORT})")
    parser.add_argument("-u", "--user", default=DEFAULT_VIRTUOSO_USER, help=f"Virtuoso user (default: {DEFAULT_VIRTUOSO_USER})")
    parser.add_argument("-k", "--password", default=DEFAULT_VIRTUOSO_PASSWORD, help=f"Virtuoso password (default: {DEFAULT_VIRTUOSO_PASSWORD})")
    
    args = parser.parse_args()
    
    if not wait_for_virtuoso(args.host):
        print("❌ Virtuoso is not ready. Exiting.")
        sys.exit(1)
    
    if not setup_fulltext_indexing(args):
        print("❌ Failed to set up full-text indexing. Exiting.")
        sys.exit(1)
    
    if not set_permissions(args):
        print("❌ Failed to set permissions. Exiting.")
        sys.exit(1)
    
    print("✅ Provenance database setup completed successfully.")
    print("ℹ️ Note: For optimal performance, consider restarting Virtuoso after this operation.")

if __name__ == "__main__":
    main()
