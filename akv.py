#!/usr/bin/env python3
import subprocess
import json
from pathlib import Path
from argparse import ArgumentParser
from tqdm import tqdm  # Progress bar library

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

def fetch_keyvault_and_secret_names():
    """Fetch both key vault names and their secret names, with a progress bar."""
    vaults = {}
    keyvault_names = fetch_keyvault_names()

    if not keyvault_names:
        print("No Key Vaults found.")
        return vaults

    print("Fetching secrets for Key Vaults...")
    with tqdm(total=len(keyvault_names), unit="vaults") as pbar:
        for vault in keyvault_names:
            try:
                result = subprocess.run(
                    ["az", "keyvault", "secret", "list", "--vault-name", vault, "--query", "[].name", "-o", "tsv"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                secret_names = result.stdout.strip().split("\n")
                vaults[vault] = secret_names
            except subprocess.CalledProcessError as e:
                print(f"Error fetching secrets for Key Vault '{vault}': {e}")
                vaults[vault] = []  # Store an empty list if fetching secrets fails
            pbar.update(1)  # Increment the progress bar
    print("Secrets fetching complete.")
    return vaults

def read_cache():
    """Read cached key vault names and their secrets. If cache file is missing, update it."""
    if not CACHE_FILE.exists():
        print("Cache file not found. Updating cache now...")
        update_cache()
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading cache file: {e}")
        return {}

def update_cache(args=None):
    """Update the cache file with fresh key vault names."""
    vault_names = fetch_keyvault_names()
    if vault_names:
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(vault_names, f)
            print(f"Cache updated successfully with key vaults! ({len(vault_names)} vaults)")
        except Exception as e:
            print(f"Error writing cache file: {e}")
    else:
        print("No vault names found. Cache update skipped.")

def update_all(args=None):
    """Update the cache file with both key vault names and their secrets."""
    vaults_with_secrets = fetch_keyvault_and_secret_names()
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(vaults_with_secrets, f)
        print(f"Cache updated successfully with key vaults and secrets!")
    except Exception as e:
        print(f"Error writing cache file: {e}")

def list_secrets(args):
    """List all secrets from a specific Key Vault using the cache."""
    cache = read_cache()
    keyvault_name = args.keyvault_name
    secrets = cache.get(keyvault_name, None)
    if secrets is None:
        print(f"No data found for Key Vault '{keyvault_name}' in the cache.")
    elif not secrets:
        print(f"No secrets found for Key Vault '{keyvault_name}'.")
    else:
        print(f"Secrets in Key Vault '{keyvault_name}':")
        for secret in secrets:
            print(secret)

def handle_completion(args=None):
    """Output cached key vault names for Bash completion."""
    cache = read_cache()
    vault_names = list(cache.keys()) if isinstance(cache, dict) else cache
    print("\n".join(vault_names))

def list_commands(args=None):
    """Output the list of registered commands for Bash completion."""
    commands = ["update", "sync", "ls", "kv", "update_all", "--complete", "--list_commands"]
    print("\n".join(commands))

def ls_cache(args=None):
    """Print the cached Key Vault names, one per line."""
    cache = read_cache()
    if isinstance(cache, dict):  # Handle nested cache structure
        vault_names = list(cache.keys())
    else:
        vault_names = cache

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

    # `update_all` subcommand
    update_all_parser = subparsers.add_parser("update_all", help="Update the cache with both key vaults and secrets.")
    update_all_parser.set_defaults(func=update_all)

    # `--complete` option (no subparser, standalone flag)
    parser.add_argument("--complete", action="store_true", help="Output cached key vault names for autocompletion.")

    # `--list_commands` option
    parser.add_argument("--list_commands", action="store_true", help="Output the list of registered commands for autocompletion.")

    args = parser.parse_args()

    # Handle commands
    if args.command:
        args.func(args)
    elif args.complete:
        handle_completion(args)
    elif args.list_commands:
        list_commands(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
