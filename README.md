# Azure Key Vault CLI Tool (`akv`)

This is a convenient CLI tool that simplifies working with Azure Key Vaults. It leverages Azure CLI (`az`) under the hood and provides caching of Key Vaults and secrets with smart autocompletion support.

## Features:

- List Azure Key Vaults and their secrets.
- Cache Key Vaults and secrets **names** locally for faster and offline browsing.
- Search vaults and secrets effectively using wildcards.
- Integrated bash-completion for easier terminal usage.
- **Does NOT cache the secret values** for security reasons.

## Requirements:
- [Python 3.7+](https://www.python.org/downloads/)
- [Azure CLI installed](https://docs.microsoft.com/cli/azure/install-azure-cli)
- `az login` executed to authenticate your session.

## Installation

### Step 1: Clone the Repository

```sh
git clone <your-repository-url>
cd <repository-name>
```

### Step 2: Create Virtual Environment & Install Dependencies:

```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Authenticate With Azure

Ensure you're logged in to your Azure account:

```sh
az login
```

### Step 4: Install the Script and Enable Bash Completion:

This will create a symlink (`akv`) to `/usr/local/bin` and enable bash autocompletion:

```sh
sudo ln -s $(realpath akv.py) /usr/local/bin/akv
sudo chmod +x /usr/local/bin/akv

# Install bash-completion
sudo cp akv-completion /etc/bash_completion.d/akv-completion

# Reload bash-completion in your current shell
source /etc/bash_completion.d/akv-completion
```

**Tip:** If you cannot add scripts into `/usr/local/bin/`, you can place the symlink in another directory already in your `PATH`.

## Usage

```sh
# Update cache with Key Vault names
akv update

# Update cache with Key Vault names AND secrets (slower but recommended periodically)
akv update_all

# List cached Key Vault names
akv ls

# List secrets from a Key Vault (cached)
akv kv <keyvault-name> ls

# Show ALL secrets and their values from a Key Vault
akv kv <keyvault-name> show

# Show specific secret's value
akv kv <keyvault-name> show <secret-name>

# Search using wildcard
akv search "myvault*secret*"

# Show secrets and values for wildcard search
akv search "myvault*secret*" show
```

### Examples:

```sh
# List key vaults
akv ls

# List secrets in my-keyvault
akv kv my-keyvault ls

# Get specific secret
akv kv my-keyvault show api-key

# Update secrets for a specific vault only
akv kv my-keyvault update

# Search secrets with wildcard
akv search "my-vault-*" show
```

## Useful tips

### Update Cache Periodically:

For optimized experience, regularly update the cache:

```sh
akv update_all
```

### Troubleshooting

- **Azure authentication errors:** Ensure you've run `az login` and that you have proper permissions for your Key Vaults.
- **Permission Issues:**  
  If you encounter permission issues when creating symlinks or installing completion scripts, ensure you're running commands with sufficient privileges (`sudo`) or use a directory you have write permission to that's listed in your `$PATH`.

---

This README should clearly guide you through project setup, installation, usage, and provide handy examples and troubleshooting guidelines.
