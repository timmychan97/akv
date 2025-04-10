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

def update_cache(args=None):
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

def list_secrets(args):
    """List all secrets from a specific Key Vault."""
    keyvault_name = args.keyvault_name
    try:
        result = subprocess.run(
            ["az", "keyvault", "secret", "list", "--vault-name", keyvault_name, "--query", "[].name", "-o", "tsv"],
            capture_output=True,
            text=True,
            check=True
        )
        secrets = result.stdout.strip().split("\n")
        print(f"Secrets in Key Vault '{keyvault_name}':")
        for secret in secrets:
            print(secret)
    except subprocess.CalledProcessError as e:
        print(f"Error fetching secrets from Key Vault '{keyvault_name}': {e}")

def handle_completion(args=None):
    """Output cached key vault names for Bash completion."""
    vault_names = read_cache()
    print("\n".join(vault_names))

def list_commands(args=None):
    """Output the list of registered commands for Bash completion."""
    commands = ["update", "sync", "ls", "kv", "--complete", "--list_commands"]
    print("\n".join(commands))

def ls_cache(args=None):
    """Print the cached Key Vault names."""
    vault_names = read_cache()
    for vault in vault_names:
        print(vault)

def main():
    parser = ArgumentParser(description="Azure Key Vault CLI tool with caching.")
    subparsers = parser.add_subparsers(dest="command")

    # `update` subcommand
    update_parser = subparsers.add_parser("update", help="Update the cache with the latest key vault names.")
    update_parser.set_defaults(func=update_cache)

    # `sync` subcommand (alias for `update`)
    sync_parser = subparsers.add_parser("sync", help="Update the cache with the latest key vault names (alias for 'update').")
    sync_parser.set_defaults(func=update_cache)

    # `ls` subcommand
    ls_parser = subparsers.add_parser("ls", help="List cached key vault names.")
    ls_parser.set_defaults(func=ls_cache)

    # `kv` subcommand
    kv_parser = subparsers.add_parser("kv", help="List all secrets from a specific Key Vault.")
    kv_parser.add_argument("keyvault_name", help="Name of the Key Vault")
    kv_parser.set_defaults(func=list_secrets)

    # `--complete` option (no subparser, standalone flag)
    parser.add_argument("--complete", action="store_true", help="Output cached key vault names for autocompletion.")

    # `--list_commands` option
    parser.add_argument("--list_commands", action="store_true", help="Output the list of registered commands for autocompletion.")

    args = parser.parse_args()

    # Handle commands
    if args.command:
        # Invoke the function associated with the subcommand
        args.func(args)
    elif args.complete:
        handle_completion(args)
    elif args.list_commands:
        list_commands(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()