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
        cache[vault] = secrets
        write_cache_to_file(cache)
    except AzureCLIError as e:
        print(f"Error updating cache for Key Vault '{keyvault_name}': {e}")

def search(args):
    """Search Key Vaults and secrets in the cache based on the provided text."""

    def create_vault_secret_map(cache):
        """Flatten vault/secret pairs into a dictionary for easier access."""
        vault_secret_map = {}
        for vault, secrets in cache.items():
            if secrets:
                for secret in secrets:
                    vault_secret_map[f"{vault}/{secret}"] = (vault, secret)
            else:
                vault_secret_map[f"{vault}/"] = (vault, None)
        return vault_secret_map

    def perform_search(vault_secret_map, search_text):
        """Find matches in the vault/secret map based on the search text."""
        if "*" in search_text:
            regex_pattern = "^" + search_text.replace("*", ".*") + "$"
            search_pattern = re.compile(regex_pattern)
            return [key for key in vault_secret_map if search_pattern.match(key)]
        return [key for key in vault_secret_map if key.startswith(search_text)]

    def display_matches_with_values(matches, vault_secret_map):
        for match in matches:
            vault, secret = vault_secret_map[match]
            if secret:
                try:
                    value = fetch_secret_value(vault, secret)
                    display_vault(vault, secret, value=value)
                except AzureCLIError as e:
                    display_vault(vault, secret, error=f"Error: {e}")
            else:
                display_vault(vault)

    cache = read_cache()
    vault_secret_map = create_vault_secret_map(cache)

    matches = perform_search(vault_secret_map, args.text)
    if not matches:
        raise Exception(f"No matches found for '{args.text}' in the cache.")

    if getattr(args, "show", False):
        display_matches_with_values(matches, vault_secret_map)
    else:
        for match in matches:
            display_vault(*vault_secret_map[match])


def display_vault(vault, secret=None, value=None, error=None):
    """Display a vault, secret, and optional value or error with color formatting."""
    LIGHT_BLUE = "\033[94m"
    YELLOW = "\033[93m"
    LIGHT_PURPLE = "\033[95m"
    LIGHT_RED = "\033[91m"
    RESET = "\033[0m"  # Reset color

    vault_display = f"{LIGHT_BLUE}{vault}/{RESET}"
    colon_display = f"{LIGHT_PURPLE}:{RESET}"

    if error:
        secret_display = f"{YELLOW}{secret}{RESET}" if secret else ""
        error_display = f"{LIGHT_RED}{error}{RESET}"
        print(f"{vault_display}{secret_display}{colon_display} {error_display}")
    elif secret:
        secret_display = f"{YELLOW}{secret}{RESET}"
        if value is not None:
            print(f"{vault_display}{secret_display}{colon_display} {value}")
        else:
            print(f"{vault_display}{secret_display}")
    else: 
        no_secrets_display = f"{LIGHT_RED}(no secrets){RESET}"
        print(f"{vault_display}{colon_display} {no_secrets_display}")


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

def add_secret_kv(args):
    """Add a secret to a Key Vault using 'kv <vault> add <secret> <value>' syntax."""
    vault = args.keyvault_name
    secret = args.secret
    value = args.value
    command = [
        "az", "keyvault", "secret", "set",
        "--vault-name", vault,
        "--name", secret,
        "--value", value,
        "-o", "tsv"
    ]
    try:
        output = run_command(command)
        print(f"Secret '{secret}' added to vault '{vault}'.")
        # Optionally update cache for this vault
        update_specific_vault(type("Args", (), {"keyvault_name": vault})())
    except AzureCLIError as e:
        print(f"\033[91mError adding secret: {e}\033[0m", file=sys.stderr)
        sys.exit(1)

def add_secret(args):
    """Add a secret to a Key Vault."""
    if "/" not in args.path:
        print("Error: Path must be in the format <vault>/<secret>", file=sys.stderr)
        sys.exit(1)
    vault, secret = args.path.split("/", 1)
    add_secret_kv(type("Args", (), {"keyvault_name": vault, "secret": secret, "value": args.value})())

def edit_secret_kv(args):
    """Edit (update) the value of a secret in a Key Vault using 'kv <vault> edit <secret> <value>' syntax."""
    vault = args.keyvault_name
    secret = args.secret
    value = args.value
    command = [
        "az", "keyvault", "secret", "set",
        "--vault-name", vault,
        "--name", secret,
        "--value", value,
        "-o", "tsv"
    ]
    try:
        output = run_command(command)
        print(f"Secret '{secret}' updated in vault '{vault}'.")
        update_specific_vault(type("Args", (), {"keyvault_name": vault})())
    except AzureCLIError as e:
        print(f"\033[91mError updating secret: {e}\033[0m", file=sys.stderr)
        sys.exit(1)

def edit_secret(args):
    """Edit (update) the value of a secret using 'edit <vault>/<secret> <value>' syntax."""
    if "/" not in args.path:
        print("Error: Path must be in the format <vault>/<secret>", file=sys.stderr)
        sys.exit(1)
    vault, secret = args.path.split("/", 1)
    edit_secret_kv(type("Args", (), {"keyvault_name": vault, "secret": secret, "value": args.value})())



def main():
    parser = ArgumentParser(description="Azure Key Vault CLI tool with caching.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("update", help="Update cache with Key Vault names.").set_defaults(func=update_cache)
    subparsers.add_parser("update_all", help="Update cache with Key Vault names and their secret names.").set_defaults(func=update_all)
    subparsers.add_parser("sync", help="Alias for `update`.").set_defaults(func=update_cache)
    subparsers.add_parser("pull", help="Alias for `update`.").set_defaults(func=update_cache)
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
    kv_subparsers.add_parser("sync", help="Alias for `update` for this Key Vault.").set_defaults(func=update_specific_vault)
    kv_subparsers.add_parser("pull", help="Alias for `update` for this Key Vault.").set_defaults(func=update_specific_vault)

    kv_add_parser = kv_subparsers.add_parser("add", help="Add a secret to this Key Vault: <secret> <value>")
    kv_add_parser.add_argument("secret", help="Name of the secret")
    kv_add_parser.add_argument("value", help="Value for the secret")
    kv_add_parser.set_defaults(func=add_secret_kv)
    kv_edit_parser = kv_subparsers.add_parser("edit", help="Edit (update) the value of a secret in this Key Vault: <secret> <value>")
    kv_edit_parser.add_argument("secret", help="Name of the secret")
    kv_edit_parser.add_argument("value", help="New value for the secret")
    kv_edit_parser.set_defaults(func=edit_secret_kv)

    search_parser = subparsers.add_parser("search", help="Search vault/secret paths in the cache.")
    search_parser.add_argument("text", help="Search text (supports wildcard * syntax for matches).")
    search_parser.set_defaults(func=search)
    search_subparsers = search_parser.add_subparsers(dest="subcommand")
    search_show_parser = search_subparsers.add_parser("show", help="List all secrets and their values from the search.")
    search_show_parser.set_defaults(func=search, show=True)

    add_parser = subparsers.add_parser("add", help="Add a secret to a Key Vault: <vault>/<secret> <value>")
    add_parser.add_argument("path", help="Path in the form <vault>/<secret>")
    add_parser.add_argument("value", help="Value for the secret")
    add_parser.set_defaults(func=add_secret)

    edit_parser = subparsers.add_parser("edit", help="Edit (update) the value of a secret: <vault>/<secret> <value>")
    edit_parser.add_argument("path", help="Path in the form <vault>/<secret>")
    edit_parser.add_argument("value", help="New value for the secret")
    edit_parser.set_defaults(func=edit_secret)

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
