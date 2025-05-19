# 🚀 Azure Key Vault CLI Tool (`akv`)

A streamlined command-line interface to effortlessly manage Azure Key Vaults, powered by [Azure CLI (`az`)](https://docs.microsoft.com/cli/azure/install-azure-cli). Boost your productivity with smart local caching, powerful wildcard searches, and supersmooth autocompletion. ⚡️🔍

---

## ✨ Features

- ✅ Quickly list Azure Key Vaults and their secrets.
- 🗃️ Local caching of Key Vault and secrets **names** for super-fast and offline access.
- 🔎 Advanced wildcard searching capability for vaults and secrets.
- 📟 Integrated bash autocompletion for smooth navigation of vaults, secrets, and subcommands.
- 🔐 **Safe & Secure**: Secret values are NEVER cached locally!

---

## 📋 Requirements

- 🐍 [Python 3.7+](https://www.python.org/downloads/)
- ☁️ [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli)
- 🔑 An authenticated Azure CLI session

---

## ⚙️ Installation

### 1️⃣ Clone the Repository

```bash
git clone <your-repository-url>
cd <repository-name>
```

### 2️⃣ Set up Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3️⃣ Install `akv` and Enable Bash Autocomplete 📟

Create a global symlink for the CLI script and enable bash autocomplete support:

```bash
# Link 'akv' script globally
sudo ln -s "$(realpath akv.py)" /usr/local/bin/akv
sudo chmod +x /usr/local/bin/akv

# Enable bash-completion
sudo cp akv-completion /etc/bash_completion.d/akv-completion

# Reload completion in current shell
source /etc/bash_completion.d/akv-completion
```

> 📝 **Note:** If permissions restrict changes in `/usr/local/bin`, you may symlink to another directory in your `$PATH`.

### 4️⃣ Authenticate to Azure

Make sure you're logged in using Azure CLI:

```bash
az login
```

---

## 🚩 Quick Start (Basic Usage)

Basic workflow examples:

```bash
# Refresh local cache (vaults only)
akv update

# Fully refresh local cache (vaults & secrets; slower)
akv update_all

# List all cached vaults
akv ls

# List cached secrets from a specific Key Vault
akv kv <keyvault-name> ls

# Display ALL secrets with their values in a Vault (requires Azure access)
akv kv <keyvault-name> show

# Display the value of a specific secret
akv kv <keyvault-name> show <secret-name>

# Add a secret to a vault
akv add <vault/secret> <value>
akv kv <keyvault-name> add <secret-name> <value>

# Edit (update) the value of a secret
akv edit <vault/secret> <new-value>
akv kv <keyvault-name> edit <secret-name> <new-value>

# Refresh secrets for 'my-keyvault' only (update cache for a specific vault)
akv kv <keyvault-name> update
akv kv <keyvault-name> sync      # alias for update
akv kv <keyvault-name> pull      # alias for update

# Powerful wildcard search
akv search "prod-*secret*"

# Show secrets and values from wildcard search matches
akv search "prod-*secret*" show
```

### 📖 Practical Examples

```bash
# List key vaults in cache
akv ls

# List secrets inside 'my-keyvault'
akv kv my-keyvault ls

# Get specific secret's value from 'my-keyvault'
akv kv my-keyvault show api-key

# Add a secret to 'my-keyvault'
akv kv my-keyvault add my-secret my-value
akv add my-keyvault/my-secret my-value

# Edit a secret in 'my-keyvault'
akv kv my-keyvault edit my-secret new-value
akv edit my-keyvault/my-secret new-value

# Refresh secrets for 'my-keyvault' only
akv kv my-keyvault update
akv kv my-keyvault sync
akv kv my-keyvault pull

# Search secrets with wildcard and show values
akv search "my-vault-*" show
```

---

## 📟 Smart Autocompletion Usage

Enjoy effortless command completion powered by smart caching of your Key Vaults and secrets:

- Typing `akv [TAB]` reveals all available subcommands.
- Typing `akv kv [TAB]` lists all cached Key Vault names.
- Typing `akv kv <keyvault-name> show [TAB]` displays all cached secret names within the selected Key Vault.

*Autocomplete makes navigation even easier—give it a try!* 🚀

---
## 🛠️ Roadmap

Exciting features planned for future releases:

- ➕ **Add Secrets**  
    - `akv kv <vault> add <secret> <value>`  
    - `akv add <vault/secret> <value>`  

- 🔀 **Move Secrets**  
    - `akv mv <vault/secret> <vault/secret>`  
    - `akv kv <vault> mv <secret> <vault/secret>`  

- 📋 **Copy Secrets**  
    - `akv cp <vault/secret> <vault/secret>`  
    - `akv kv <vault> cp <secret> <vault/secret>`  

- ❌ **Delete Secrets**  
    - `akv rm <vault/secret>`  
    - `akv kv <vault> rm <secret>`  

Stay tuned for these updates to make `akv` even more powerful and versatile! 🚀

## 📌 Best Practices & Tips

- ▶️ **Keep Cache Updated:** Periodically refresh your cache for the latest vaults and secrets:
  ```sh
  akv update_all
  ```

- 🔒 **Stay Secure:** Remember, secret values are NEVER cached locally.

---

## 📡 Troubleshooting FAQ

- ❌ **Authentication problems?**  
  Ensure you've authenticated using:
  ```sh
  az login
  ```
  Also confirm your Azure account has permission to list and access your key vaults.

- 🚧 **Symlink or file permissions issue?**  
  Use `sudo` if needed. Alternatively, create the symlink in a directory included in your `$PATH` and accessible without elevated privileges.

---

> 💡 This README is designed to help you quickly set up, utilize, and troubleshoot the `akv` CLI tool efficiently. Boost your productivity today with `akv`! ⚡️🔑
