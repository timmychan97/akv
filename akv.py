#!/usr/bin/env python3
import sys
import subprocess
import json
import re
from pathlib import Path
from argparse import ArgumentParser
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# Location for the cache file
CACHE_FILE = Path.home() / ".akv_cache.json"


class AzureCLIError(Exception):
    """Custom exception for Azure CLI errors."""
    def __init__(self, message, command=None):
        super().__init__(message)
        self.command = command


def run_command(command):
    """Utility function to safely run subprocess commands with error handling."""
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # Raise a custom AzureCLIError with the relevant error message
        error_message = e.stderr.strip()
        if "Failed to establish a new connection" in error_message:
            raise AzureCLIError(f"Unable to connect to the Key Vault: {error_message}", command=command)
        elif "ERROR:" in error_message:
            raise AzureCLIError(f"Azure CLI returned an error: {error_message}", command=command)
        # Handle generic subprocess errors
        raise AzureCLIError(f"Command failed: {' '.join(command)}\n{error_message}", command=command)
    except FileNotFoundError as e:
        print(f"Azure CLI not found or not installed: {e}")
        return None


def fetch_keyvault_names():
    """Fetch key vault names using `az keyvault list`."""
    command = [
        "az", "keyvault", "list", "--query", "[].name", "-o", "tsv"
    ]
    result = run_command(command)
    return result.split("\n") if result else []


def fetch_secrets_for_vault(vault):
    """Fetch secret names for a specific Key Vault, with error handling for missing vaults."""
    command = [
        "az", "keyvault", "secret", "list", "--vault-name", vault,
        "--query", "[].name", "-o", "tsv"
    ]
    result = run_command(command)
    if result is None:  # Check if the command failed
        print(f"Error: Key Vault '{vault}' does not exist or is unavailable.")
        return vault, None
    secret_names = result.split("\n") if result else []
    return vault, secret_names


def fetch_keyvault_and_secret_names():
    """Fetch both key vault names and their secret names, using parallel execution."""
    vaults = {}
    keyvault_names = fetch_keyvault_names()
    if not keyvault_names:
        print("No Key Vaults found.")
        return vaults
    print(f"Fetching secrets for {len(keyvault_names)} Key Vault(s)...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_vault = {
            executor.submit(fetch_secrets_for_vault, vault): vault
            for vault in keyvault_names
        }
        with tqdm(total=len(future_to_vault), unit="vault") as pbar:
            for future in as_completed(future_to_vault):
                vault, secrets = future.result()
                vaults[vault] = secrets
                pbar.update(1)  # Increment the progress bar
    return vaults


def fetch_secret_value(vault_name, secret_name):
    """Fetch the value of a specific secret from a Key Vault."""
    command = [
        "az", "keyvault", "secret", "show", "--vault-name", vault_name,
        "--name", secret_name, "--query", "value", "-o", "tsv"
    ]
    return run_command(command)


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


def write_cache_to_file(cache):
    """Utility function to write cache to file, ensuring it is sorted alphabetically."""
    # Ensure the dictionary is sorted alphabetically by key (vault names)
    # and the secrets list is also sorted
    sorted_cache = {
        vault: sorted(secrets) if secrets else []
        for vault, secrets in sorted(cache.items())
    }
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(sorted_cache, f, indent=4)
            f.write('\n')
        print(f"Cache updated successfully.")
    except Exception as e:
        print(f"Error writing to cache file: {e}")


def update_cache(args=None):
    """Update the cache file with fresh key vault names."""
    keyvault_names = fetch_keyvault_names()
    if keyvault_names:
        cache = {kv: [] for kv in keyvault_names}  # Empty list for secrets
        write_cache_to_file(cache)
    else:
        print("No Key Vault names found. Cache update skipped.")


def update_all(args=None):
    """Update the cache file with both key vault names and their secrets."""
    vaults_with_secrets = fetch_keyvault_and_secret_names()
    write_cache_to_file(vaults_with_secrets)


def list_secrets(args):
    """List all secrets in a specific Key Vault using cached data."""
    cache = read_cache()
    keyvault_name = args.keyvault_name
    secrets = cache.get(keyvault_name)
    if secrets is None:
        print(f"No data found for Key Vault '{keyvault_name}' in the cache.")
    elif not secrets:
        print(f"No secrets found for Key Vault '{keyvault_name}'.")
    else:
        for secret in secrets:
            print(secret)


def show_secrets(args):
    """List all secrets and their values from a specific Key Vault."""
    cache = read_cache()
    keyvault_name = args.keyvault_name
    secret_name = args.secret_name
    secrets = cache.get(keyvault_name)
    if secret_name:
        value = fetch_secret_value(keyvault_name, secret_name)
        if value is not None:
            print(f"Value of secret '{secret_name}': {value}")
    elif secrets is None:
        print(f"No data found for Key Vault '{keyvault_name}' in the cache.")
    elif not secrets:
        print(f"No secrets found for Key Vault '{keyvault_name}'.")
    else:
        print(f"Secrets and their values in Key Vault '{keyvault_name}':")
        print("-------------------------------------")
        for secret in secrets:
            value = fetch_secret_value(keyvault_name, secret)
            print(f"{secret}: {value}")


def update_specific_vault(args):
    """Update the cache for a specific Key Vault."""
    keyvault_name = args.keyvault_name
    print(f"Updating cache for Key Vault: {keyvault_name}")
    try:
        vault, secrets = fetch_secrets_for_vault(keyvault_name)
        cache = read_cache()
        if isinstance(cache, list):
            cache = {kv: [] for kv in cache}
        cache[vault] = secrets
        write_cache_to_file(cache)
    except AzureCLIError as e:
        print(f"Error updating cache for Key Vault '{keyvault_name}': {e}")


def search(args):
    """Search Key Vaults and secrets in the cache based on the provided text."""
    cache = read_cache()
    if isinstance(cache, list):
        combined_data = {kv: [] for kv in cache}
    else:
        combined_data = cache

    search_text = args.text
    search_results = []
    for vault, secrets in combined_data.items():
        if not secrets:
            search_results.append(f"{vault}/")
        if isinstance(secrets, list):
            search_results.extend(f"{vault}/{secret}" for secret in secrets)

    if '*' in search_text:
        regex_pattern = "^" + search_text.replace("*", ".*") + "$"
        search_pattern = re.compile(regex_pattern)
        matches = [item for item in search_results if search_pattern.match(item)]
    else:
        matches = [item for item in search_results if item.startswith(search_text)]

    if not matches:
        raise Exception(f"No matches found for '{search_text}' in the cache.")
    for match in matches:
        print(match)


def handle_completion(args=None):
    """Output cached key vault names for Bash completion."""
    cache = read_cache()
    vault_names = list(cache.keys()) if isinstance(cache, dict) else cache
    print("\n".join(vault_names))


def list_commands(args=None):
    """Output the list of registered commands for Bash completion."""
    commands = ["update", "sync", "ls", "kv", "update_all", "search", "--complete", "--list_commands"]
    print("\n".join(commands))


def ls_cache(args=None):
    """Print the cached Key Vault names, one per line."""
    cache = read_cache()
    if isinstance(cache, dict):
        vault_names = list(cache.keys())
    else:
        vault_names = cache
    for vault in vault_names:
        print(vault)


def main():
    parser = ArgumentParser(description="Azure Key Vault CLI tool with caching.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("update", help="Update cache with Key Vault names.").set_defaults(func=update_cache)
    subparsers.add_parser("update_all", help="Update cache with Key Vault names and their secret names.").set_defaults(func=update_all)
    subparsers.add_parser("sync", help="Alias for `update`.").set_defaults(func=update_cache)
    subparsers.add_parser("ls", help="List all cached Key Vault names.").set_defaults(func=ls_cache)

    kv_parser = subparsers.add_parser("kv", help="Manage secrets from a specific Key Vault.")
    kv_parser.add_argument("keyvault_name", help="Name of the Key Vault")
    kv_parser.set_defaults(func=list_secrets)
    kv_subparsers = kv_parser.add_subparsers(dest="subcommand")
    kv_ls_parser = kv_subparsers.add_parser("ls", help="List all secrets' names in the Key Vault.")
    kv_ls_parser.set_defaults(func=list_secrets)
    kv_show_parser = kv_subparsers.add_parser("show", help="List all secrets or a specific secret value in the Key Vault.")
    kv_show_parser.add_argument("secret_name", nargs="?", help="Name of the secret (optional)")
    kv_show_parser.set_defaults(func=show_secrets)
    kv_update_parser = kv_subparsers.add_parser("update", help="Update cache for a specific Key Vault.")
    kv_update_parser.set_defaults(func=update_specific_vault)

    search_parser = subparsers.add_parser("search", help="Search vault/secret paths in the cache.")
    search_parser.add_argument("text", help="Search text (supports wildcard * syntax for matches).")
    search_parser.set_defaults(func=search)

    parser.add_argument("--complete", action="store_true", help="Output cached Key Vault names for autocompletion.")
    parser.add_argument("--list_commands", action="store_true", help="Output the list of all available main commands.")

    args = parser.parse_args()
    if args.command:
        try:
            args.func(args)
        except Exception as e:
            print(f"\033[91mError: {e}\033[0m", file=sys.stderr)  # Print error message in red
            sys.exit(1)
    elif args.complete:
        handle_completion(args)
    elif args.list_commands:
        list_commands(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
