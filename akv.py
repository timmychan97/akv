#!/usr/bin/env python3

import subprocess
import json
from pathlib import Path
from argparse import ArgumentParser

# Define the location for the cache file
CACHE_FILE = Path.home() / ".akv_cache.json"

def fetch_keyvault_names():
    """Fetch key vault names using `az keyvault list`."""
    try:
        result = subprocess.run(
            ["az", "keyvault", "list", "--query", "[].name", "-o", "tsv"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().split("\n")
    except subprocess.CalledProcessError as e:
        print(f"Error fetching keyvault names: {e}")
        return []

def read_cache():
    """Read cached key vault names. If cache file is missing, update it."""
    if not CACHE_FILE.exists():
        print("Cache file not found. Updating cache now...")
        update_cache()

    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading cache file: {e}")
        return []

def update_cache():
    """Update the cache file with fresh key vault names."""
    vault_names = fetch_keyvault_names()
    if vault_names:
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(vault_names, f)
            print(f"Cache updated successfully! ({len(vault_names)} vaults)")
        except Exception as e:
            print(f"Error writing cache file: {e}")
    else:
        print("No vault names found. Cache update skipped.")

def handle_completion():
    """Output cached key vault names for Bash completion."""
    vault_names = read_cache()
    print("\n".join(vault_names))

def main():
    parser = ArgumentParser(description="Azure Key Vault CLI tool with caching.")
    
    # Add optional arguments (flags) for syncing cache
    parser.add_argument("--update", action="store_true", help="Update the cache with the latest key vault names.")
    parser.add_argument("--sync", action="store_true", help="Update the cache with the latest key vault names (alternative to --update).")
    parser.add_argument("--complete", action="store_true", help="Output cached key vault names for autocompletion.")
    parser.add_argument("keyvault", nargs="?", help="Key Vault name (optional).")
    args = parser.parse_args()

    # Handle subcommands and arguments
    if args.update or args.sync:
        update_cache()
    elif args.complete:
        handle_completion()
    elif args.keyvault:
        print(f"Selected Key Vault: {args.keyvault}")
    else:
        print("No Key Vault selected. Use '--update' or '--sync' to refresh cache, and '--complete' for suggestions.")

if __name__ == "__main__":
    main()