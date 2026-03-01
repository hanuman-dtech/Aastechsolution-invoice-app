# Infrastructure Beginner Guide — Step-by-Step

> **Audience**: Absolute beginners who want to understand how this project deploys to the cloud.
> Read this from top to bottom; every concept is explained before it is used.

---

## Table of Contents

1. [What Problem Does This Solve?](#1-what-problem-does-this-solve)
2. [Key Concepts (Plain English)](#2-key-concepts-plain-english)
3. [Tools You Need](#3-tools-you-need)
4. [Project Folder Map](#4-project-folder-map)
5. [The Big Picture — How Everything Connects](#5-the-big-picture--how-everything-connects)
6. [Step-by-Step: What Each File Does](#6-step-by-step-what-each-file-does)
   - [6.1 Versions & Providers (versions.tf, providers.tf)](#61-versions--providers)
   - [6.2 Variables (variables.tf)](#62-variables)
   - [6.3 Backend State (backend.hcl)](#63-backend-state)
   - [6.4 Main Orchestration (main.tf)](#64-main-orchestration)
   - [6.5 Outputs (outputs.tf)](#65-outputs)
7. [Module-by-Module Walkthrough](#7-module-by-module-walkthrough)
   - [7.1 resource-group Module](#71-resource-group-module)
   - [7.2 network Module](#72-network-module)
   - [7.3 security Module](#73-security-module)
   - [7.4 compute Module](#74-compute-module)
   - [7.5 iam Module](#75-iam-module)
8. [How the CI/CD Pipelines Work](#8-how-the-cicd-pipelines-work)
   - [8.1 terraform-pr.yml (Pull Request Checks)](#81-terraform-pryml-pull-request-checks)
   - [8.2 terraform-apply.yml (Deploying to Azure)](#82-terraform-applyyml-deploying-to-azure)
   - [8.3 Other Workflows](#83-other-workflows)
9. [Security & RBAC Explained](#9-security--rbac-explained)
   - [9.1 What is RBAC?](#91-what-is-rbac)
   - [9.2 How Our RBAC Works](#92-how-our-rbac-works)
   - [9.3 Private Endpoints (Zero-Trust Networking)](#93-private-endpoints-zero-trust-networking)
   - [9.4 Managed Identity (No Passwords for Apps)](#94-managed-identity-no-passwords-for-apps)
10. [Governance & Code Ownership](#10-governance--code-ownership)
11. [Running It Yourself — Step-by-Step Commands](#11-running-it-yourself--step-by-step-commands)
12. [Glossary](#12-glossary)
13. [Complete Session Log — Everything We Did, In Order](#13-complete-session-log--everything-we-did-in-order)
    - [Phase 1: Install Tools](#phase-1-install-tools)
    - [Phase 2: Azure Login](#phase-2-azure-login)
    - [Phase 3: Provision Terraform State Backend](#phase-3-provision-terraform-state-backend)
    - [Phase 4: Write Terraform Modules & RBAC](#phase-4-write-terraform-modules--rbac)
    - [Phase 5: Create CI/CD Pipelines](#phase-5-create-cicd-pipelines)
    - [Phase 6: Create Governance Documents](#phase-6-create-governance-documents)
    - [Phase 7: Configure GitHub OIDC](#phase-7-configure-github-oidc-passwordless-cicd)
    - [Phase 8: Grant Azure Roles to the Service Principal](#phase-8-grant-azure-roles-to-the-service-principal)
    - [Phase 9: Set GitHub Repository Secrets](#phase-9-set-github-repository-secrets)
    - [Phase 10: Create GitHub Environments](#phase-10-create-github-environments)
    - [Phase 11: Enable Branch Protection](#phase-11-enable-branch-protection)
    - [Phase 12: Harden .gitignore](#phase-12-harden-gitignore)
    - [Phase 13: Commit, Push, and Open Pull Request](#phase-13-commit-push-and-open-pull-request)
    - [Phase 14: What Happens Now (Automatically)](#phase-14-what-happens-now-automatically)

---

## 1. What Problem Does This Solve?

You have an **Invoice Enterprise Application** (a web app with a backend API + frontend). It needs a place to run in the cloud. Instead of clicking around in the Azure Portal to create servers, databases, and networks by hand, we use **Terraform** to write down *exactly* what we want in code files. Then we run a single command and everything gets created automatically. This approach is called **Infrastructure as Code (IaC)**.

**Why is this better than clicking in a portal?**

| Manual (Portal)                                | Infrastructure as Code (Terraform)                    |
| ---------------------------------------------- | ----------------------------------------------------- |
| Hard to repeat exactly                         | Run the same code in any environment                  |
| No audit trail of who changed what             | Every change is a Git commit with history             |
| One person makes a mistake → outage            | Code review catches mistakes before they go live      |
| Hard to have identical dev and prod             | Same modules, different variable files                |
| Cleanup is guesswork                           | `terraform destroy` removes everything it created     |

---

## 2. Key Concepts (Plain English)

| Concept                | What It Means                                                                                                                              |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Azure**              | Microsoft's cloud — a giant collection of data centers where you rent servers, networks, and services                                       |
| **Subscription**       | Your billing boundary in Azure. Think of it as your "account bucket" where resources live and bills are sent                                |
| **Tenant**             | Your organization's identity directory in Azure (Microsoft Entra ID). Manages users, groups, permissions                                    |
| **Resource Group**     | A folder-like container in Azure. All related resources (server, network, database) go into one group                                       |
| **Terraform**          | A tool that reads `.tf` files (your "blueprints") and creates/updates/deletes cloud resources to match                                      |
| **Module**             | A reusable package of Terraform code. Like a function in programming — takes inputs, creates resources, returns outputs                     |
| **State file**         | A JSON file Terraform keeps to remember what it already created. Without it, Terraform wouldn't know what exists in Azure                   |
| **Backend**            | Where the state file is stored. We store it in Azure Blob Storage so the whole team shares one truth                                        |
| **RBAC**               | Role-Based Access Control — giving people/apps specific permissions (like "can read" vs "can edit") instead of all-or-nothing admin access  |
| **Private Endpoint**   | A way to access Azure services through a private IP address inside your network, instead of over the public internet                        |
| **Managed Identity**   | Azure gives your app an auto-managed identity (like a badge) so it can access other services without storing passwords                      |
| **OIDC**               | OpenID Connect — a protocol that lets GitHub Actions prove its identity to Azure without storing secret passwords                            |
| **CI/CD**              | Continuous Integration / Continuous Deployment — automatic workflows that test and deploy your code when you push to GitHub                  |
| **GitHub Actions**     | GitHub's built-in automation engine. Runs workflows defined in YAML files under `.github/workflows/`                                        |

---

## 3. Tools You Need

| Tool             | Version    | What It Does                              | Installation                                          |
| ---------------- | ---------- | ----------------------------------------- | ----------------------------------------------------- |
| **Azure CLI**    | 2.60+      | Talk to Azure from your terminal          | `curl -sL https://aka.ms/InstallAzureCLIDeb \| sudo bash` |
| **Terraform**    | 1.7 – 1.x | Read `.tf` files and create cloud stuff   | `sudo snap install terraform --classic`               |
| **Git**          | any        | Version control for your code             | Usually pre-installed on Linux                        |
| **VS Code**      | any        | Code editor                               | Already using it!                                     |

### Verify installation

```bash
az --version        # Should show 2.60+
terraform --version # Should show 1.7+
git --version       # Should show any version
```

---

## 4. Project Folder Map

Here is the infrastructure part of the project. Each file has a specific job:

```
infra/terraform/
│
├── README.md                      ← Overview documentation
│
├── modules/                       ← REUSABLE BUILDING BLOCKS
│   ├── resource-group/            ← Creates an Azure Resource Group
│   │   ├── main.tf                   (the actual resource definition)
│   │   ├── variables.tf              (inputs the module accepts)
│   │   └── outputs.tf                (values the module returns)
│   │
│   ├── network/                   ← Creates VNet + Subnets + Diagnostics
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── security/                  ← Creates ACR + Key Vault + Private Endpoints
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── compute/                   ← Creates App Service Plan + Web App
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   └── iam/                       ← Creates Role Assignments (RBAC permissions)
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
│
└── envs/                          ← ENVIRONMENT-SPECIFIC CONFIGURATION
    ├── dev/                       ← Development environment
    │   ├── versions.tf               (which Terraform/provider versions to use)
    │   ├── providers.tf              (configure the Azure provider)
    │   ├── backend.hcl               (where to store state — not in Git!)
    │   ├── backend.hcl.example       (template for backend.hcl)
    │   ├── main.tf                   (wire all modules together for dev)
    │   ├── variables.tf              (all variable definitions for dev)
    │   ├── terraform.tfvars.example  (template for variable values)
    │   └── outputs.tf                (what to display after apply)
    │
    └── prod/                      ← Production environment (same structure)
        ├── versions.tf
        ├── providers.tf
        ├── backend.hcl
        ├── ...
```

**Key rule**: Modules are *generic building blocks*. Environments (`dev/`, `prod/`) *use* those blocks with different settings.

---

## 5. The Big Picture — How Everything Connects

Here is the flow from your code to running cloud resources:

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR COMPUTER (WSL2)                      │
│                                                             │
│  1. You edit .tf files in VS Code                           │
│  2. You run: terraform plan  → shows what WILL change       │
│  3. You run: terraform apply → CREATES resources in Azure   │
│                                                             │
│  OR... you push code to GitHub and CI/CD does it for you:   │
│                                                             │
│  4. Open Pull Request → terraform-pr.yml runs checks        │
│  5. Merge to main    → terraform-apply.yml deploys          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AZURE CLOUD                               │
│                                                             │
│   ┌─────────────────────────────┐                           │
│   │ rg-tfstate-shared           │  ← State storage          │
│   │ └── sttfstate385403         │     (remembers what       │
│   │     └── tfstate/            │      Terraform created)   │
│   │         ├── dev.tfstate     │                           │
│   │         └── prod.tfstate    │                           │
│   └─────────────────────────────┘                           │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ rg-invoice-dev  (Resource Group)                    │   │
│   │                                                     │   │
│   │  ┌─── VNet (10.20.0.0/16) ──────────────────────┐  │   │
│   │  │                                               │  │   │
│   │  │  ┌── app subnet (10.20.1.0/24) ──────────┐   │  │   │
│   │  │  │  App Service (your web app runs here)  │   │  │   │
│   │  │  └────────────────────────────────────────┘   │  │   │
│   │  │                                               │  │   │
│   │  │  ┌── private-endpoints subnet ────────────┐   │  │   │
│   │  │  │  Private Endpoint → ACR                │   │  │   │
│   │  │  │  Private Endpoint → Key Vault          │   │  │   │
│   │  │  │  Private Endpoint → Web App            │   │  │   │
│   │  │  └────────────────────────────────────────┘   │  │   │
│   │  └───────────────────────────────────────────────┘  │   │
│   │                                                     │   │
│   │  Log Analytics Workspace (collects all logs)        │   │
│   │  Container Registry (stores Docker images)          │   │
│   │  Key Vault (stores secrets securely)                │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ rg-invoice-prod  (same layout, stricter settings)   │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Step-by-Step: What Each File Does

### 6.1 Versions & Providers

**File**: `envs/dev/versions.tf`

```hcl
terraform {
  required_version = ">= 1.7.0, < 2.0.0"   # We need Terraform 1.7 or newer, but not 2.x

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"          # The Azure provider plugin
      version = "~> 4.0"                     # Any 4.x version (4.0, 4.1, 4.62, etc.)
    }
    random = {
      source  = "hashicorp/random"           # Generates random strings (for unique names)
      version = "~> 3.6"
    }
  }

  backend "azurerm" {}                       # State is stored in Azure (details in backend.hcl)
}
```

**What this means line by line:**

- `required_version`: Makes sure nobody accidentally runs this with an incompatible Terraform version
- `required_providers`: Tells Terraform to download the Azure plugin so it knows how to talk to Azure
- `backend "azurerm" {}`: "Store my state file in Azure Blob Storage" (the actual connection details come from `backend.hcl`)

---

**File**: `envs/dev/providers.tf`

```hcl
provider "azurerm" {
  features {}                                # Required by Azure provider (even if empty)
  subscription_id = var.subscription_id      # Which Azure subscription to use
  tenant_id       = var.tenant_id            # Which Azure AD tenant to authenticate against
}

data "azurerm_client_config" "current" {}    # Looks up "who am I?" — returns your user/SP info
```

**What this means:**

- `provider "azurerm"`: Configures the Azure connection. Think of it as "log me into this specific Azure account"
- `data "azurerm_client_config"`: A *data source* — it doesn't create anything, it just reads information. Here it reads the current logged-in user's details (used later to give yourself Key Vault access)

---

### 6.2 Variables

**File**: `envs/dev/variables.tf`

Variables are like function parameters. They let you customize the infrastructure without changing code.

```hcl
variable "environment" {
  description = "Environment name."   # Human-readable explanation
  type        = string                # Must be a text value
  default     = "dev"                 # If nobody provides a value, use "dev"
}

variable "subscription_id" {
  description = "Azure subscription ID."
  type        = string                # No default — you MUST provide this
}
```

**Why are there so many variables?** Because we want to reuse the same code for dev and prod, just with different values. For example:

| Variable           | Dev Value             | Prod Value            |
| ------------------ | --------------------- | --------------------- |
| `environment`      | `"dev"`               | `"prod"`              |
| `vnet_address_space` | `["10.20.0.0/16"]` | `["10.30.0.0/16"]`   |
| `app_service_sku`  | `"P1v3"`              | `"P1v3"` (or bigger) |

**Where do values come from?** From `terraform.tfvars` (a file you create locally from the `.example` template) or from `-var` flags in the CI/CD pipeline.

---

### 6.3 Backend State

**File**: `envs/dev/backend.hcl`

```hcl
resource_group_name  = "rg-tfstate-shared"    # Azure RG holding the storage account
storage_account_name = "sttfstate385403"       # Storage account name (globally unique)
container_name       = "tfstate"               # Blob container inside the storage account
key                  = "invoice-enterprise/dev.tfstate"  # Path to the state file
use_azuread_auth     = true                    # Use Azure AD auth (not storage keys)
```

**What this means:**

- Every time you run `terraform apply`, Terraform writes what it created to a **state file**
- This state file is stored in Azure Blob Storage (not on your laptop!) so that:
  - Your teammate can also run Terraform and it knows what already exists
  - CI/CD pipelines can read the same state
  - If your laptop dies, the state is safe in the cloud
- `key` is different per environment: `dev.tfstate` vs `prod.tfstate` — this keeps dev and prod completely separate

---

### 6.4 Main Orchestration

**File**: `envs/dev/main.tf` — This is the **heart of the configuration**. It wires all modules together.

**Step 1: Generate unique names**

```hcl
resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}
```

Azure requires globally unique names for many services. Adding a random 5-character suffix (like `a3k8x`) ensures names don't collide with other Azure customers worldwide.

**Step 2: Calculate resource names**

```hcl
locals {
  env_suffix = lower(var.environment)        # "dev" or "prod"
  suffix     = random_string.suffix.result   # "a3k8x"

  resource_group_name   = "rg-invoice-dev"
  vnet_name             = "vnet-invoice-dev"
  log_analytics_name    = "law-invoice-dev-a3k8x"
  acr_name              = "acrinvoicedeva3k8x"      # No hyphens! ACR rule
  key_vault_name        = "kv-invoice-dev-a3k8x"    # Max 24 characters
  app_name              = "app-invoice-dev-a3k8x"
}
```

`locals` are like internal variables — calculated values you use throughout the file.

**Step 3: Call modules one by one**

```hcl
# 1️⃣ Create the Resource Group (the "folder" for everything)
module "resource_group" {
  source   = "../../modules/resource-group"
  name     = local.resource_group_name
  location = var.location
  tags     = local.common_tags
}

# 2️⃣ Create Log Analytics (collects all monitoring logs)
resource "azurerm_log_analytics_workspace" "this" {
  name                = local.log_analytics_name
  resource_group_name = module.resource_group.name     # Uses output from step 1
  location            = module.resource_group.location
  sku                 = "PerGB2018"
  retention_in_days   = 30                             # Keep logs for 30 days (90 in prod)
  ...
}

# 3️⃣ Create the Network (VNet + Subnets)
module "network" {
  source              = "../../modules/network"
  name                = local.vnet_name
  resource_group_name = module.resource_group.name
  address_space       = var.vnet_address_space         # e.g., 10.20.0.0/16
  subnets = {
    app = {
      address_prefixes = var.app_subnet_prefixes       # e.g., 10.20.1.0/24
      delegation = { ... }                             # Reserved for App Service
    }
    private-endpoints = {
      address_prefixes = var.private_endpoint_subnet_prefixes  # e.g., 10.20.2.0/24
    }
  }
}

# 4️⃣ Create Security resources (ACR + Key Vault + Private Endpoints)
module "security" {
  source                    = "../../modules/security"
  acr_name                  = local.acr_name
  key_vault_name            = local.key_vault_name
  vnet_id                   = module.network.vnet_id
  private_endpoint_subnet_id = module.network.subnet_ids["private-endpoints"]
  ...
}

# 5️⃣ Create Compute (App Service Plan + Web App)
module "compute" {
  source            = "../../modules/compute"
  app_name          = local.app_name
  acr_id            = module.security.acr_id
  key_vault_id      = module.security.key_vault_id
  app_subnet_id     = module.network.subnet_ids["app"]
  ...
}

# 6️⃣ Create IAM (Role Assignments / Permissions)
module "iam" {
  source            = "../../modules/iam"
  resource_group_id = module.resource_group.id
  acr_id            = module.security.acr_id
  key_vault_id      = module.security.key_vault_id
  ...
}
```

**Notice the pattern**: Each module *depends on* outputs from previous modules. Terraform automatically figures out the order:

```
resource-group → log_analytics → network → security → compute → iam
```

---

### 6.5 Outputs

**File**: `envs/dev/outputs.tf`

```hcl
output "resource_group_name" {
  value       = module.resource_group.name
  description = "Resource Group name."
}

output "acr_login_server" {
  value       = module.security.acr_login_server
  description = "ACR login server for CI image pushes."
}
```

After `terraform apply` finishes, these values are printed on screen. They tell you the actual names of resources that were created (useful because names include random suffixes).

---

## 7. Module-by-Module Walkthrough

### 7.1 resource-group Module

**Location**: `modules/resource-group/main.tf`

```hcl
resource "azurerm_resource_group" "this" {
  name     = var.name       # e.g., "rg-invoice-dev"
  location = var.location   # e.g., "canadacentral"
  tags     = var.tags       # Labels like { project = "invoice-enterprise" }
}
```

**What it does**: Creates an Azure Resource Group — the top-level container for all other resources. Think of it as a folder. When you delete this, everything inside it gets deleted too.

**Inputs**: `name`, `location`, `tags`
**Outputs**: `id` (unique Azure ID), `name`, `location`

---

### 7.2 network Module

**Location**: `modules/network/main.tf`

**What it creates**:

| Resource                    | Purpose                                                                |
| --------------------------- | ---------------------------------------------------------------------- |
| **Virtual Network (VNet)**  | Your own private network in Azure, like a private LAN in the cloud     |
| **Subnets**                 | Subdivisions of the VNet for different purposes                        |
| **Diagnostic Settings**     | Sends network logs to Log Analytics for monitoring                     |

**Subnets explained**:

```
VNet: 10.20.0.0/16  (65,536 IP addresses)
│
├── app subnet: 10.20.1.0/24  (256 IPs)
│   └── This is where the Web App connects via "VNet Integration"
│       It has a "delegation" to Microsoft.Web/serverFarms, meaning
│       only App Service can use this subnet
│
└── private-endpoints subnet: 10.20.2.0/24  (256 IPs)
    └── This is where Private Endpoints live — private doorways
        into ACR, Key Vault, and the Web App itself
```

**Key concept — Delegation**: When a subnet is "delegated" to a service (like App Service), Azure reserves it exclusively for that service. No other resource type can be placed there.

**Key concept — Diagnostics**: Every resource automatically sends its logs and metrics to Log Analytics. This is done with `azurerm_monitor_diagnostic_setting` using a `dynamic` block that discovers all available log categories automatically.

---

### 7.3 security Module

**Location**: `modules/security/main.tf`

**What it creates**:

| Resource                       | Purpose                                                                          |
| ------------------------------ | -------------------------------------------------------------------------------- |
| **Container Registry (ACR)**   | Stores Docker images of your app. Premium SKU for private endpoints              |
| **Key Vault**                  | Stores secrets (DB passwords, API keys) — NOT in code!                           |
| **Private DNS Zones**          | Makes `*.azurecr.io` and `*.vaultcore.azure.net` resolve to private IPs          |
| **Private Endpoints**          | Creates private IP addresses for ACR and Key Vault inside your VNet              |
| **Diagnostic Settings**        | Sends ACR/KV logs to Log Analytics                                               |

**Security features explained:**

```hcl
resource "azurerm_container_registry" "this" {
  sku                           = "Premium"     # Required for private endpoints
  admin_enabled                 = false          # No admin user — use managed identity instead
  public_network_access_enabled = false          # Cannot be reached from the internet
}
```

- **`admin_enabled = false`**: The admin account is a shared credential. Disabling it forces you to use proper identity (managed identity or RBAC)
- **`public_network_access_enabled = false`**: The registry is invisible from the internet. Only resources inside your VNet can reach it

```hcl
resource "azurerm_key_vault" "this" {
  sku_name                      = "premium"
  rbac_authorization_enabled    = true      # Use Azure RBAC instead of access policies
  public_network_access_enabled = false     # Private only
  purge_protection_enabled      = true      # Deleted secrets can be recovered for 90 days
  soft_delete_retention_days    = 90        # Don't permanently delete for 90 days
}
```

- **`rbac_authorization_enabled = true`**: Permissions are managed via Azure RBAC roles, not the older "access policies" approach. This is the modern best practice
- **`purge_protection_enabled = true`**: Even if someone deletes a secret, it can be recovered. Prevents accidental (or malicious) permanent data loss

**Private Endpoint flow (simplified)**:

```
                    Public Internet
                         ❌ BLOCKED

            ┌────────────────────────────────┐
            │       Your VNet                │
            │                                │
            │  App Service ──────────────────┤
            │       │                        │
            │       │ (private network)      │
            │       ▼                        │
            │  Private Endpoint ── ACR       │
            │  (10.20.2.x)                   │
            │                                │
            │  Private Endpoint ── Key Vault │
            │  (10.20.2.y)                   │
            └────────────────────────────────┘
```

Instead of your app talking to `myregistry.azurecr.io` over the public internet, the Private DNS Zone makes that hostname resolve to a private IP (like `10.20.2.4`) inside your VNet. Traffic never leaves your private network.

---

### 7.4 compute Module

**Location**: `modules/compute/main.tf`

**What it creates**:

| Resource                       | Purpose                                                     |
| ------------------------------ | ----------------------------------------------------------- |
| **App Service Plan**           | The "server" that runs your app (you choose the size)       |
| **Linux Web App**              | Your actual web application running in a Docker container   |
| **Role Assignments**           | Gives the app permission to pull from ACR and read secrets  |
| **Private Endpoint + DNS**     | Makes the web app accessible only via private network       |
| **Diagnostic Settings**        | Sends app logs to Log Analytics                             |

**Key settings explained:**

```hcl
resource "azurerm_linux_web_app" "this" {
  https_only                    = true       # Only HTTPS allowed, no HTTP
  public_network_access_enabled = false      # Not accessible from internet directly

  identity {
    type = "SystemAssigned"   # Azure creates an identity for this app automatically
  }

  site_config {
    always_on              = true            # Keep the app running (don't sleep)
    minimum_tls_version    = "1.2"           # Reject old/insecure TLS versions
    ftps_state             = "Disabled"      # No FTP uploads (security risk)
    vnet_route_all_enabled = true            # All outbound traffic goes through VNet

    container_registry_use_managed_identity = true  # Pull images using identity, not password
  }
}
```

**Managed Identity in action:**

```
┌─────────────────────────────────┐
│  Web App                        │
│  Identity: "I am app-invoice-   │
│            dev-a3k8x"           │
│                                 │
│  1. I need to pull my Docker    │
│     image from ACR              │
│     → Azure checks: does this   │
│       identity have AcrPull?    │
│     → YES (role assignment)     │
│     → Image pulled ✅            │
│                                 │
│  2. I need to read a secret     │
│     from Key Vault              │
│     → Azure checks: does this   │
│       identity have KV Secrets  │
│       User?                     │
│     → YES (role assignment)     │
│     → Secret read ✅             │
└─────────────────────────────────┘
```

No passwords or keys are stored anywhere. The app proves who it is using its Azure-managed identity.

---

### 7.5 iam Module

**Location**: `modules/iam/main.tf`

**What it does**: Creates **role assignments** — rules that say "this person/group/app is allowed to do X on resource Y."

There are 8 role types managed here:

| Role                         | Scope              | Who Gets It                     | What They Can Do                    |
| ---------------------------- | ------------------ | ------------------------------- | ----------------------------------- |
| **Contributor**              | Resource Group     | Platform engineers              | Create/modify/delete resources      |
| **User Access Administrator**| Resource Group     | IAM admin group                 | Manage who has access to what       |
| **Reader**                   | Resource Group     | Operations/support              | View resources but can't change them|
| **Security Reader**          | Resource Group     | Security/compliance team        | View security settings and alerts   |
| **Log Analytics Reader**     | Log Analytics      | Observability/SOC team          | Read monitoring logs                |
| **AcrPush**                  | Container Registry | CI/CD build pipelines           | Push Docker images                  |
| **Key Vault Secrets Officer**| Key Vault          | Secrets operations team         | Read/write/delete secrets           |
| **Website Contributor**      | App Service        | Application operations team     | Manage app configuration/deploys    |

**How `for_each` works:**

```hcl
resource "azurerm_role_assignment" "rg_contributor" {
  for_each             = toset(var.resource_group_contributor_principal_ids)
  scope                = var.resource_group_id
  role_definition_name = "Contributor"
  principal_id         = each.value
}
```

If you provide 3 group IDs in `resource_group_contributor_principal_ids`, Terraform creates 3 separate role assignments. If you provide 0 (the default), none are created. This is the `for_each` pattern — loop over a set of values.

---

## 8. How the CI/CD Pipelines Work

### 8.1 terraform-pr.yml (Pull Request Checks)

**When it runs**: Every time someone opens or updates a Pull Request that changes files in `infra/terraform/`.

**What it does (in order)**:

```
Step 1: terraform fmt -check
        └── "Is the code formatted correctly?"
        └── Fails if someone didn't run `terraform fmt`

Step 2: terraform init -backend=false + terraform validate
        └── "Is the code syntactically valid?"
        └── -backend=false means it doesn't connect to Azure (faster, no auth needed)

Step 3: tflint
        └── "Are there common mistakes or deprecated features?"
        └── A linting tool specifically for Terraform

Step 4: trivy IaC scan
        └── "Are there security misconfigurations?"
        └── Scans for HIGH/CRITICAL issues and FAILS the build if found
        └── Example: "You left public access enabled on Key Vault" → FAIL

Step 5: terraform plan (for both dev AND prod)
        └── "What WOULD change if we applied this?"
        └── Creates a plan artifact (saved file) for audit trail
        └── Does NOT actually change anything in Azure
```

**Why this matters**: Before any code reaches `main`, it must pass ALL these checks. This prevents mistakes from reaching production.

---

### 8.2 terraform-apply.yml (Deploying to Azure)

**When it runs**: When code is merged to the `main` branch (or manually triggered).

**What it does**:

```
Job 1: apply-dev
        └── Runs terraform apply on the DEV environment
        └── Uses the "dev" GitHub Environment (may require approval)

        ↓ (only if dev succeeds)

Job 2: apply-prod
        └── Runs terraform apply on the PROD environment
        └── Uses the "prod" GitHub Environment (REQUIRES approval from reviewers)
        └── Only runs on the main branch
```

**Key safety features**:

- **Sequential**: prod only deploys AFTER dev succeeds. If dev breaks, prod is safe
- **Concurrency lock**: Only one apply can run at a time (`cancel-in-progress: false`). Prevents two people from deploying simultaneously
- **Environment protection**: prod requires human approval before deploying
- **OIDC authentication**: Uses `azure/login@v2` with federated credentials — no passwords stored in GitHub

---

### 8.3 Other Workflows

| Workflow                | What It Does                                                        |
| ----------------------- | ------------------------------------------------------------------- |
| **codeql.yml**          | Scans Python and JavaScript/TypeScript code for security bugs       |
| **dependency-review.yml**| Checks if new dependencies have known vulnerabilities              |
| **secret-scan.yml**     | Uses Gitleaks to detect accidentally committed secrets/passwords    |

---

## 9. Security & RBAC Explained

### 9.1 What is RBAC?

**RBAC = Role-Based Access Control**

Instead of giving everyone "admin" access, you give specific roles:

```
❌ BAD:  "Everyone is an admin and can do anything"
✅ GOOD: "Alice can READ logs, Bob can DEPLOY apps, Carol can MANAGE secrets"
```

In Azure, a Role Assignment has three parts:

```
WHO    +    WHAT         +    WHERE
(principal)  (role)          (scope)
───────────────────────────────────────
Group-A   +  Contributor  +  rg-invoice-dev
Group-B   +  Reader       +  rg-invoice-dev
CI-SP     +  AcrPush      +  acrinvoicedeva3k8x
```

### 9.2 How Our RBAC Works

```
┌───────────────────────────────────────────────────────────────┐
│                   Microsoft Entra ID (Azure AD)               │
│                                                               │
│   Groups (recommended):                                       │
│   ┌─────────────────────┐  ┌──────────────────────┐          │
│   │ platform-engineers  │  │ security-team        │          │
│   │ (Contributor)       │  │ (Security Reader)    │          │
│   └─────────────────────┘  └──────────────────────┘          │
│   ┌─────────────────────┐  ┌──────────────────────┐          │
│   │ iam-admins          │  │ soc-team             │          │
│   │ (User Access Admin) │  │ (Log Analytics Reader)│         │
│   └─────────────────────┘  └──────────────────────┘          │
│                                                               │
│   Service Principals:                                         │
│   ┌─────────────────────┐                                    │
│   │ github-actions-sp   │  ← CI/CD uses this identity       │
│   │ (Contributor +      │                                    │
│   │  User Access Admin) │                                    │
│   └─────────────────────┘                                    │
└───────────────────────────────────────────────────────────────┘
              │
              ▼ (role assignments created by Terraform)
┌───────────────────────────────────────────────────────────────┐
│                   Azure Resources                             │
│                                                               │
│   rg-invoice-dev:                                             │
│     platform-engineers → Contributor                          │
│     iam-admins         → User Access Administrator            │
│     ops-support        → Reader                               │
│     security-team      → Security Reader                      │
│                                                               │
│   law-invoice-dev-xxxxx:                                      │
│     soc-team           → Log Analytics Reader                 │
│                                                               │
│   acrinvoicedevxxxxx:                                         │
│     ci-build-sp        → AcrPush                              │
│                                                               │
│   kv-invoice-dev-xxxxx:                                       │
│     secrets-ops        → Key Vault Secrets Officer            │
│                                                               │
│   app-invoice-dev-xxxxx:                                      │
│     app-ops-team       → Website Contributor                  │
│     (auto) web app MI  → AcrPull + KV Secrets User            │
└───────────────────────────────────────────────────────────────┘
```

**Rule**: Always use **Entra groups**, not individual user accounts. If someone leaves the company, you remove them from the group — all their permissions disappear automatically.

---

### 9.3 Private Endpoints (Zero-Trust Networking)

**The Problem**: By default, Azure services (ACR, Key Vault) are accessible from the internet. Anyone who guesses the URL could try to attack them.

**The Solution**: Private Endpoints create a **private IP address** for the service inside your VNet. The service's public endpoint is disabled.

```
WITHOUT Private Endpoints:            WITH Private Endpoints:
                                      
Internet ──→ ACR (public IP)          Internet ──→ ❌ BLOCKED
Internet ──→ Key Vault (public IP)    
                                      VNet ──→ Private IP ──→ ACR     ✅
                                      VNet ──→ Private IP ──→ Key Vault ✅
```

**Private DNS Zones** make this seamless. When your app asks for `myregistry.azurecr.io`, the private DNS zone answers with the private IP instead of the public one.

---

### 9.4 Managed Identity (No Passwords for Apps)

**The Problem**: Your app needs to access ACR (to pull images) and Key Vault (to read secrets). Normally you'd need a username/password.

**The Solution**: Azure assigns your Web App a **System-Assigned Managed Identity**. This is like giving your app an employee badge. Azure manages the credentials automatically — they rotate, they never appear in code, they can't be leaked.

```hcl
identity {
  type = "SystemAssigned"  # Azure: "I'll give this app an identity automatically"
}
```

Then we create role assignments so Azure knows what this identity is allowed to do:

```hcl
# The web app can pull Docker images from the registry
resource "azurerm_role_assignment" "acr_pull" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_linux_web_app.this.identity[0].principal_id
}

# The web app can read secrets from Key Vault
resource "azurerm_role_assignment" "key_vault_secrets_user" {
  scope                = var.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_web_app.this.identity[0].principal_id
}
```

---

## 10. Governance & Code Ownership

### CODEOWNERS (`.github/CODEOWNERS`)

This file tells GitHub "who must review changes to which files":

```
*                              @hanuman-dtech/platform-admins    # Everything needs platform review
/infra/terraform/**            @hanuman-dtech/security-team      # Infra changes ALSO need security
/.github/workflows/**          @hanuman-dtech/security-team      # CI/CD changes need security
/invoice-enterprise/backend/** @hanuman-dtech/backend-team       # Backend code needs backend team
/invoice-enterprise/frontend/**@hanuman-dtech/frontend-team      # Frontend code needs frontend team
```

### ORG_DEVOPS_RULES.md

A governance document that defines the rules everyone must follow:

- Use Entra groups for RBAC (no individual user assignments)
- Protect `main` branch with 2 approvals minimum
- Use OIDC for CI/CD (no client secrets)
- Fail builds on HIGH/CRITICAL security findings
- Store state remotely, never locally
- Never store credentials in repository files

---

## 11. Running It Yourself — Step-by-Step Commands

### First-Time Setup (already done in our session)

```bash
# 1. Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# 2. Log in to Azure
az login --use-device-code
# → Opens a browser, you enter the code shown in terminal

# 3. Verify your account
az account show
# Should show your subscription name and ID
```

### Initialize Terraform (already done)

```bash
# Navigate to the dev environment
cd infra/terraform/envs/dev

# 4. Create your variable file from the example
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your real values:
#   subscription_id = "ffaabce9-a623-45ba-8d10-da4c30d74c1f"
#   tenant_id       = "8da61a47-5619-4370-9bd5-15bb6dd5445f"

# 5. Initialize Terraform (downloads providers, connects to backend)
terraform init -backend-config=backend.hcl
```

**What `terraform init` does:**

1. Downloads the Azure provider plugin (~100MB)
2. Downloads the random provider plugin
3. Connects to Azure Blob Storage to read/create the state file
4. Sets up the `.terraform/` directory (local cache, never commit this!)

### Plan and Apply

```bash
# 6. See what Terraform WOULD create (dry run)
terraform plan -var-file=terraform.tfvars

# Output looks like:
#   + azurerm_resource_group.this   (create)
#   + azurerm_virtual_network.this  (create)
#   ... (many resources)
#   Plan: 25 to add, 0 to change, 0 to destroy.

# 7. Actually create everything (requires confirmation)
terraform apply -var-file=terraform.tfvars
# Type "yes" when prompted
```

### Common Commands Reference

| Command                          | What It Does                                          |
| -------------------------------- | ----------------------------------------------------- |
| `terraform init`                 | Set up working directory & download plugins           |
| `terraform plan`                 | Preview what would change (doesn't touch Azure)       |
| `terraform apply`                | Create/update resources in Azure                      |
| `terraform destroy`              | Delete ALL resources Terraform created                |
| `terraform fmt`                  | Auto-format your `.tf` files                          |
| `terraform validate`             | Check syntax without connecting to Azure              |
| `terraform state list`           | Show all resources Terraform is managing              |
| `terraform output`               | Show output values (resource names, IDs, etc.)        |

---

## 12. Glossary

| Term                          | Definition                                                                                   |
| ----------------------------- | -------------------------------------------------------------------------------------------- |
| **ACR**                       | Azure Container Registry — stores Docker images                                              |
| **App Service**               | Azure's managed web hosting platform — runs your container                                   |
| **App Service Plan**          | The underlying compute (CPU/RAM) behind an App Service                                       |
| **Backend (Terraform)**       | Where Terraform stores its state file (Azure Blob Storage for us)                            |
| **CIDR notation**             | `10.20.0.0/16` means "10.20.x.x with 65,536 addresses". The `/16` sets the network size     |
| **Container**                 | A lightweight, portable package containing your app and all its dependencies                  |
| **Data source**               | A Terraform block that reads existing information (doesn't create anything)                   |
| **Delegation**                | Reserving a subnet exclusively for a specific Azure service                                  |
| **Diagnostic Setting**        | Configuration that sends a resource's logs/metrics to Log Analytics                          |
| **Docker image**              | A snapshot of your app + OS + dependencies, ready to run as a container                      |
| **Entra ID**                  | Microsoft's identity service (formerly Azure Active Directory / AAD)                         |
| **Federated credential**      | OIDC trust relationship — lets GitHub Actions authenticate to Azure without a password       |
| **`for_each`**                | Terraform loop — creates one resource instance for each item in a set                        |
| **HCL**                       | HashiCorp Configuration Language — the syntax Terraform files use                            |
| **Key Vault**                 | Azure's secrets management service — secure storage for passwords, keys, certificates        |
| **`locals`**                  | Terraform internal variables — calculated values used within a configuration                 |
| **Log Analytics Workspace**   | Azure's log aggregation service — collects and queries logs from all resources               |
| **Managed Identity**          | An Azure-managed credential for a resource — no passwords to manage                          |
| **Module**                    | A reusable Terraform building block (folder with `.tf` files)                                |
| **OIDC**                      | OpenID Connect — protocol for passwordless authentication between services                   |
| **Output**                    | A value Terraform displays after apply — useful for getting resource names/IDs               |
| **Principal ID**              | A unique identifier for a user, group, or service principal in Entra ID                      |
| **Private DNS Zone**          | Makes Azure service hostnames resolve to private IPs inside your VNet                        |
| **Private Endpoint**          | A network interface with a private IP that connects to an Azure service                      |
| **Provider**                  | A Terraform plugin that knows how to manage a specific cloud (azurerm = Azure)               |
| **Purge Protection**          | Prevents permanent deletion of Key Vault items for a set retention period                    |
| **RBAC**                      | Role-Based Access Control — assigning specific permissions to specific identities             |
| **Resource**                  | A Terraform block that creates something in Azure                                            |
| **Resource Group**            | An Azure container that holds related resources together                                     |
| **SKU**                       | Stock Keeping Unit — Azure's way of saying "pricing tier" or "size"                          |
| **Soft Delete**               | Deleted items are kept recoverable for a grace period instead of permanent deletion           |
| **State file**                | JSON file tracking what Terraform has created — the "source of truth"                        |
| **Subnet**                    | A subdivision of a VNet with its own IP range                                                |
| **System-Assigned Identity**  | An identity Azure creates and manages automatically for a specific resource                  |
| **Tags**                      | Key-value labels on Azure resources for organization, billing, and governance                 |
| **Tenant**                    | An organization's Azure AD / Entra ID directory                                              |
| **TFLint**                    | A Terraform linting tool that catches common mistakes                                        |
| **Trivy**                     | A security scanner that finds misconfigurations in infrastructure code                       |
| **Variable**                  | A Terraform input parameter — makes code configurable without editing directly               |
| **VNet**                      | Virtual Network — your private network in the Azure cloud                                    |
| **VNet Integration**          | Connecting an App Service to a VNet so its outbound traffic flows through the private network |
| **WSL2**                      | Windows Subsystem for Linux 2 — run a real Linux environment inside Windows                  |
| **Zero-Trust**                | Security model: "never trust, always verify" — no implicit access based on network location  |

---

## 13. Complete Session Log — Everything We Did, In Order

This section documents **every step** performed during our infrastructure bootstrap session, in chronological order. Each step shows the command that was run, what it does, why it was needed, and what came after.

---

### Phase 1: Install Tools

**Step 1 — Detect the operating system**

```bash
cat /etc/os-release
```

**Result**: Ubuntu 24.04.3 LTS running on WSL2 (Windows Subsystem for Linux).
**Why**: We needed to know which package manager and install commands to use.

---

**Step 2 — Install Azure CLI**

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

**What this does**: Downloads and runs Microsoft's official install script for Debian/Ubuntu. It adds the Microsoft package repo and installs `az` CLI.
**Result**: `az version 2.83.0` installed at `/usr/bin/az`.

---

**Step 3 — Confirm Terraform is available**

```bash
terraform --version
```

**Result**: Terraform v1.14.6 at `/snap/bin/terraform` (was already installed via snap).

---

### Phase 2: Azure Login

**Step 4 — Log in to Azure**

```bash
az login --use-device-code
```

**What this does**: Prints a URL and a code. You open the URL in a browser, enter the code, and sign in with your Microsoft account. The CLI then gets a token.
**Why `--use-device-code`**: WSL2 can't always open a browser automatically, so device code flow is more reliable.

**Result**: Logged in as `anusharao.t9479@outlook.com`.

---

**Step 5 — Verify subscription and tenant**

```bash
az account show --query "{subscriptionId:id, tenantId:tenantId, user:user.name}" -o json
```

**Result**:
```json
{
  "subscriptionId": "ffaabce9-a623-45ba-8d10-da4c30d74c1f",
  "tenantId": "8da61a47-5619-4370-9bd5-15bb6dd5445f",
  "user": "anusharao.t9479@outlook.com"
}
```

These IDs are used throughout — in Terraform variables, GitHub secrets, and role assignments.

---

### Phase 3: Provision Terraform State Backend

**Why do we need this?** Terraform keeps a "state file" that tracks what resources it created. This file must be stored somewhere safe and shared. We store it in Azure Blob Storage.

---

**Step 6 — Register the Microsoft.Storage provider**

```bash
az provider show -n Microsoft.Storage --query registrationState -o tsv
# Result: "NotRegistered"

az provider register -n Microsoft.Storage --wait
# Result: "Registered"
```

**What this does**: Azure has many "resource providers" — each one unlocks a type of service. `Microsoft.Storage` was not registered in our new subscription, so we couldn't create storage accounts. `--wait` blocks until registration completes.

**Why it was needed**: The first attempt to create a storage account failed with `SubscriptionNotFound` because the provider wasn't registered.

---

**Step 7 — Create the state storage resource group**

```bash
az group create --name rg-tfstate-shared --location canadacentral
```

**What this does**: Creates a Resource Group (a container/folder) called `rg-tfstate-shared` in Canada Central region.
**Why**: Every Azure resource must live inside a Resource Group.

---

**Step 8 — Create the storage account**

```bash
az storage account create \
  --name sttfstate385403 \
  --resource-group rg-tfstate-shared \
  --location canadacentral \
  --sku Standard_LRS \
  --kind StorageV2 \
  --https-only true \
  --allow-blob-public-access false \
  --allow-shared-key-access false \
  --min-tls-version TLS1_2
```

**What each flag means**:

| Flag | Meaning |
|------|---------|
| `--name sttfstate385403` | Globally unique name (3-24 chars, lowercase + numbers only, no hyphens!) |
| `--sku Standard_LRS` | Cheapest tier: locally redundant storage |
| `--https-only true` | Reject unencrypted HTTP connections |
| `--allow-blob-public-access false` | Nobody can make blobs public |
| `--allow-shared-key-access false` | Disable storage keys; force Azure AD auth only |
| `--min-tls-version TLS1_2` | Reject old TLS versions |

**Why the name `sttfstate385403`**: First attempt `test-terraform-storage-account` failed because hyphens are not allowed. We used `st` (storage) + `tfstate` (purpose) + `385403` (random suffix for uniqueness).

---

**Step 9 — Create the blob container**

```bash
az storage container create \
  --account-name sttfstate385403 \
  --name tfstate \
  --auth-mode login
```

**What this does**: Creates a blob container named `tfstate` inside the storage account. A container is like a folder for blobs (files).
**`--auth-mode login`**: Use our Azure AD login (not a storage key) to authenticate.

---

**Step 10 — Grant yourself Storage Blob Data Contributor**

```bash
az role assignment create \
  --role "Storage Blob Data Contributor" \
  --assignee "37804b6f-dd4a-4e77-9fb3-87d8d6dd679c" \
  --scope "/subscriptions/ffaabce9-a623-45ba-8d10-da4c30d74c1f/resourceGroups/rg-tfstate-shared/providers/Microsoft.Storage/storageAccounts/sttfstate385403"
```

**What this does**: Gives your user account permission to read/write blobs in the storage account.
**Why**: Since we disabled shared key access (`--allow-shared-key-access false`), the only way to access blobs is through Azure AD data-plane roles. Without this, `terraform init` would get a 403 Forbidden error.

**Important**: RBAC assignments take ~30 seconds to propagate. The first `terraform init` attempt failed with 403, but after waiting 30 seconds it succeeded.

---

**Step 11 — Initialize Terraform with remote backend**

```bash
# Wait for RBAC propagation
sleep 30

# Dev environment
cd infra/terraform/envs/dev
terraform init -backend-config=backend.hcl -reconfigure

# Prod environment
cd ../prod
terraform init -backend-config=backend.hcl -reconfigure
```

**What `-backend-config=backend.hcl` does**: Feeds the storage account connection details from `backend.hcl` into the `backend "azurerm" {}` block in `versions.tf`.

**What `-reconfigure` does**: Forces Terraform to re-read the backend configuration even if already initialized.

**Result**: "Successfully configured the backend 'azurerm'!" for both environments.

---

### Phase 4: Write Terraform Modules & RBAC

This phase happened before the backend was provisioned (you can write code before having Azure resources).

**Step 12 — Create 5 Terraform modules**

We created 5 modules in `infra/terraform/modules/`:

| Order | Module | Files Created | What It Manages |
|-------|--------|--------------|-----------------|
| 1 | `resource-group/` | main.tf, variables.tf, outputs.tf | Azure Resource Group |
| 2 | `network/` | main.tf, variables.tf, outputs.tf | VNet + Subnets + Diagnostics |
| 3 | `security/` | main.tf, variables.tf, outputs.tf | ACR + Key Vault + Private Endpoints + DNS |
| 4 | `compute/` | main.tf, variables.tf, outputs.tf | App Service Plan + Web App + Identity |
| 5 | `iam/` | main.tf, variables.tf, outputs.tf | 8 RBAC role assignments |

**Step 13 — Create environment configurations**

For each environment (dev, prod), created: `main.tf`, `variables.tf`, `outputs.tf`, `providers.tf`, `versions.tf`, `backend.hcl.example`, `terraform.tfvars.example`

**Step 14 — Validate everything**

```bash
# Format all files consistently
terraform fmt -recursive infra/terraform/

# Validate syntax for both environments
terraform -chdir=infra/terraform/envs/dev init -backend=false
terraform -chdir=infra/terraform/envs/dev validate
# Result: "Success! The configuration is valid."

terraform -chdir=infra/terraform/envs/prod init -backend=false
terraform -chdir=infra/terraform/envs/prod validate
# Result: "Success! The configuration is valid."
```

**`-backend=false`**: Skips connecting to Azure — just checks syntax locally. Useful for validation during development.

---

### Phase 5: Create CI/CD Pipelines

Created 5 GitHub Actions workflow files in `.github/workflows/`:

| Workflow | Trigger | What It Does |
|----------|---------|-------------|
| `terraform-pr.yml` | Pull Request | fmt → validate → tflint → trivy scan → terraform plan |
| `terraform-apply.yml` | Push to `main` | terraform apply (dev first, then prod with approval) |
| `codeql.yml` | Push/PR/weekly | Security scanning for Python + JS/TS code |
| `dependency-review.yml` | Pull Request | Block PRs with vulnerable dependencies |
| `secret-scan.yml` | Push/PR | Gitleaks scans for accidentally committed secrets |

Also created `dependabot.yml` for automated dependency updates.

---

### Phase 6: Create Governance Documents

| File | Purpose |
|------|---------|
| `.github/CODEOWNERS` | Defines who must review changes to which files |
| `.github/ORG_DEVOPS_RULES.md` | Enterprise DevOps rules: RBAC, branch protection, CI/CD security |
| `.github/BRANCH_PROTECTION.md` | Recommended branch protection settings |

---

### Phase 7: Configure GitHub OIDC (Passwordless CI/CD)

**Why OIDC?** Our DevOps rules say: "Use workload identities (OIDC) for CI/CD; prohibit client secrets for pipeline auth." OIDC lets GitHub Actions prove its identity to Azure without storing any password or secret key.

---

**Step 15 — Create an Entra app registration**

```bash
az ad app create --display-name "github-actions-invoice-app" \
  --query "{appId:appId, id:id}" -o json
```

**Result**:
```json
{
  "appId": "480c825d-b4e5-4cab-8dc7-ea60134d6185",
  "id": "995a8d8a-e27a-4cf2-9891-9cd30584a4ad"
}
```

**What this does**: Creates an "App Registration" in Microsoft Entra ID. This is like creating an employee profile for GitHub Actions. Two IDs are returned:
- `appId` (also called Client ID) — the public identifier, used in GitHub secrets
- `id` (Object ID) — the internal database ID, used for API calls

---

**Step 16 — Create a Service Principal for the app**

```bash
az ad sp create --id "480c825d-b4e5-4cab-8dc7-ea60134d6185" \
  --query "{servicePrincipalId:id, appId:appId}" -o json
```

**Result**:
```json
{
  "appId": "480c825d-b4e5-4cab-8dc7-ea60134d6185",
  "servicePrincipalId": "70cf322c-c1ab-4fcf-af43-d2818a508cb1"
}
```

**What's the difference between App Registration and Service Principal?**
- **App Registration** = the identity definition (like a passport)
- **Service Principal** = the identity in your specific tenant (like a work badge for that passport)

You need both. The SP is what gets role assignments.

---

**Step 17 — Add 3 Federated Credentials**

Each credential creates a trust relationship between a specific GitHub Actions context and this Azure identity.

```bash
# Credential 1: For the DEV environment
az ad app federated-credential create \
  --id "995a8d8a-e27a-4cf2-9891-9cd30584a4ad" \
  --parameters '{
    "name": "github-actions-dev",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:hanuman-dtech/Aastechsolution-invoice-app:environment:dev",
    "audiences": ["api://AzureADTokenExchange"],
    "description": "GitHub Actions OIDC for dev environment"
  }'
```

```bash
# Credential 2: For the PROD environment
az ad app federated-credential create \
  --id "995a8d8a-e27a-4cf2-9891-9cd30584a4ad" \
  --parameters '{
    "name": "github-actions-prod",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:hanuman-dtech/Aastechsolution-invoice-app:environment:prod",
    "audiences": ["api://AzureADTokenExchange"],
    "description": "GitHub Actions OIDC for prod environment"
  }'
```

```bash
# Credential 3: For Pull Requests (needed for terraform plan during PRs)
az ad app federated-credential create \
  --id "995a8d8a-e27a-4cf2-9891-9cd30584a4ad" \
  --parameters '{
    "name": "github-actions-pr",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:hanuman-dtech/Aastechsolution-invoice-app:pull_request",
    "audiences": ["api://AzureADTokenExchange"],
    "description": "GitHub Actions OIDC for pull requests"
  }'
```

**How this works (simplified)**:

```
GitHub Actions workflow starts
    │
    ▼
GitHub: "I am running a job in the 'dev' environment
         for repo hanuman-dtech/Aastechsolution-invoice-app.
         Here's a signed token proving it."
    │
    ▼
Azure: "Let me check... I have a federated credential that says:
        - Issuer must be: token.actions.githubusercontent.com ✅
        - Subject must be: repo:hanuman-dtech/...:environment:dev ✅
        - Audience must be: api://AzureADTokenExchange ✅
        OK, I trust you. Here's an Azure access token."
    │
    ▼
GitHub Actions: "Thanks! I'll use this token to run Terraform."
```

**No passwords are ever stored or transmitted.** The trust is based on cryptographic tokens signed by GitHub.

---

**Step 18 — Verify all federated credentials**

```bash
az ad app federated-credential list \
  --id "995a8d8a-e27a-4cf2-9891-9cd30584a4ad" \
  --query "[].{name:name, subject:subject}" -o table
```

**Result**:
```
Name                 Subject
-------------------  ---------------------------------------------------------------
github-actions-pr    repo:hanuman-dtech/Aastechsolution-invoice-app:pull_request
github-actions-prod  repo:hanuman-dtech/Aastechsolution-invoice-app:environment:prod
github-actions-dev   repo:hanuman-dtech/Aastechsolution-invoice-app:environment:dev
```

---

### Phase 8: Grant Azure Roles to the Service Principal

**Why**: The SP needs permission to actually do things in Azure. We follow least privilege — only the minimum roles required.

---

**Step 19 — Grant Contributor (subscription scope)**

```bash
az role assignment create \
  --assignee-object-id "70cf322c-c1ab-4fcf-af43-d2818a508cb1" \
  --assignee-principal-type ServicePrincipal \
  --role "Contributor" \
  --scope "/subscriptions/ffaabce9-a623-45ba-8d10-da4c30d74c1f"
```

**What Contributor allows**: Create, modify, and delete resources (Resource Groups, VNets, Web Apps, etc.). Does NOT allow managing permissions (RBAC).

---

**Step 20 — Grant User Access Administrator (subscription scope)**

```bash
az role assignment create \
  --assignee-object-id "70cf322c-c1ab-4fcf-af43-d2818a508cb1" \
  --assignee-principal-type ServicePrincipal \
  --role "User Access Administrator" \
  --scope "/subscriptions/ffaabce9-a623-45ba-8d10-da4c30d74c1f"
```

**What User Access Administrator allows**: Create/delete role assignments. Needed because our Terraform code creates role assignments (the IAM module, the compute module's AcrPull/KV assignments).

---

**Step 21 — Grant Storage Blob Data Contributor (state storage account)**

```bash
az role assignment create \
  --assignee-object-id "70cf322c-c1ab-4fcf-af43-d2818a508cb1" \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/ffaabce9-a623-45ba-8d10-da4c30d74c1f/resourceGroups/rg-tfstate-shared/providers/Microsoft.Storage/storageAccounts/sttfstate385403"
```

**What this allows**: Read/write blobs in the state storage account. Needed for `terraform init` to access the state file.
**Why scoped to the storage account only**: Least privilege — CI/CD only needs blob access on this one storage account, not all storage accounts in the subscription.

---

**Step 22 — Verify all role assignments**

```bash
az role assignment list \
  --assignee "70cf322c-c1ab-4fcf-af43-d2818a508cb1" \
  --all \
  --query "[].{role:roleDefinitionName, scope:scope}" -o table
```

**Result**:
```
Role                           Scope
-----------------------------  ---------------------------
Contributor                    /subscriptions/ffaabce9-...
User Access Administrator      /subscriptions/ffaabce9-...
Storage Blob Data Contributor  .../storageAccounts/sttfstate385403
```

---

### Phase 9: Set GitHub Repository Secrets

**Why**: The CI/CD workflows reference `${{ secrets.AZURE_CLIENT_ID }}` etc. These values must be stored in GitHub's encrypted secrets storage.

---

**Step 23 — Set all 6 secrets**

```bash
# Azure identity
gh secret set AZURE_CLIENT_ID --body "480c825d-b4e5-4cab-8dc7-ea60134d6185"
gh secret set AZURE_TENANT_ID --body "8da61a47-5619-4370-9bd5-15bb6dd5445f"
gh secret set AZURE_SUBSCRIPTION_ID --body "ffaabce9-a623-45ba-8d10-da4c30d74c1f"

# Terraform state backend
gh secret set TFSTATE_RESOURCE_GROUP --body "rg-tfstate-shared"
gh secret set TFSTATE_STORAGE_ACCOUNT --body "sttfstate385403"
gh secret set TFSTATE_CONTAINER --body "tfstate"
```

**What `gh secret set` does**: Encrypts the value and stores it in the repository settings. Only GitHub Actions workflows can read it — nobody can view the value, not even repo admins.

---

**Step 24 — Verify secrets exist**

```bash
gh secret list
```

**Result**:
```
NAME                     UPDATED
AZURE_CLIENT_ID          less than a minute ago
AZURE_SUBSCRIPTION_ID    less than a minute ago
AZURE_TENANT_ID          less than a minute ago
TFSTATE_CONTAINER        less than a minute ago
TFSTATE_RESOURCE_GROUP   less than a minute ago
TFSTATE_STORAGE_ACCOUNT  less than a minute ago
```

**How workflows use these secrets**:

```yaml
# In terraform-pr.yml:
- name: Azure Login (OIDC)
  uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}       # ← From our secret
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}       # ← From our secret
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}  # ← From our secret
```

---

### Phase 10: Create GitHub Environments

**Why**: Our `terraform-apply.yml` workflow uses `environment: dev` and `environment: prod`. These must exist in GitHub for OIDC to work (the federated credential subjects reference them).

---

**Step 25 — Create dev environment (no gates)**

```bash
gh api --method PUT repos/hanuman-dtech/Aastechsolution-invoice-app/environments/dev
```

**What this does**: Creates a GitHub Environment named "dev". No protection rules — deployments to dev happen automatically.

---

**Step 26 — Get your GitHub user ID**

```bash
gh api user --jq '.id'
# Result: 237657826
```

**Why**: The GitHub API needs numeric IDs for reviewers, not usernames.

---

**Step 27 — Create prod environment (with reviewer requirement)**

```bash
gh api --method PUT repos/hanuman-dtech/Aastechsolution-invoice-app/environments/prod \
  -f 'reviewers[][type]=User' \
  -F 'reviewers[][id]=237657826'
```

**What this does**: Creates a GitHub Environment named "prod" with a required reviewer. When the `apply-prod` job runs, it will **PAUSE** and wait for `hanuman-dtech` (you) to click "Approve" in the GitHub UI before proceeding.

**Per DevOps rules**: "prod must require at least 2 reviewers." Currently we have 1 (solo project). Add more as team grows.

---

### Phase 11: Enable Branch Protection

**Why**: DevOps rules say "Protect main branch: minimum approvals, code-owner review required, stale approvals dismissed."

---

**Step 28 — Apply branch protection rules to `main`**

```bash
gh api --method PUT repos/hanuman-dtech/Aastechsolution-invoice-app/branches/main/protection \
  -F 'required_status_checks[strict]=true' \
  -f 'required_status_checks[contexts][]=quality-gates' \
  -F 'enforce_admins=true' \
  -F 'required_pull_request_reviews[dismiss_stale_reviews]=true' \
  -F 'required_pull_request_reviews[require_code_owner_reviews]=true' \
  -F 'required_pull_request_reviews[required_approving_review_count]=1' \
  -F 'restrictions=null' \
  -F 'required_linear_history=true' \
  -F 'allow_force_pushes=false' \
  -F 'allow_deletions=false'
```

**What each setting does**:

| Setting | Value | Meaning |
|---------|-------|---------|
| `required_status_checks[strict]` | `true` | Branch must be up-to-date with main before merging |
| `required_status_checks[contexts]` | `quality-gates` | The `terraform-pr.yml` quality-gates job must pass |
| `enforce_admins` | `true` | Even repo admins must follow these rules (no bypassing) |
| `dismiss_stale_reviews` | `true` | If you push new commits, old approvals are invalidated |
| `require_code_owner_reviews` | `true` | People listed in CODEOWNERS must approve |
| `required_approving_review_count` | `1` | At least 1 approval needed (increase for teams) |
| `required_linear_history` | `true` | No merge commits — clean, linear history |
| `allow_force_pushes` | `false` | Cannot overwrite history on main |
| `allow_deletions` | `false` | Cannot delete the main branch |

---

### Phase 12: Harden .gitignore

**Why**: DevOps rules say "Never store credentials/secrets in repository files."

---

**Step 29 — Update .gitignore to block sensitive files**

Added these patterns to `.gitignore`:

```gitignore
# Environment files (NEVER commit secrets)
.env
.env.*
!.env.example

# Terraform sensitive files
**/backend.hcl
!**/backend.hcl.example
```

**What this prevents**:
- `.env` files with passwords → blocked
- `.env.example` with placeholder values → allowed (note the `!` negation)
- `backend.hcl` with real storage account names → blocked
- `backend.hcl.example` with template values → allowed

---

### Phase 13: Commit, Push, and Open Pull Request

**Step 30 — Stage and commit all changes**

```bash
git add .gitignore .github/ docs/INFRASTRUCTURE_BEGINNER_GUIDE.md infra/
git status --short
# Shows 41 files staged

git commit -m "feat: enterprise Azure IaC, RBAC, CI/CD pipelines, and beginner docs"
```

**Why this commit message format**: Follows [Conventional Commits](https://www.conventionalcommits.org/) — `feat:` prefix means a new feature. This is important for automated changelogs and semantic versioning.

---

**Step 31 — Push to the remote branch**

```bash
git push origin chore/ui-backend-followup-20260301
```

**Result**: 41 files, 3,398 lines pushed to GitHub.

---

**Step 32 — Open (or update) the Pull Request**

```bash
# This PR already existed, so we updated its title and description:
gh pr edit 5 \
  --title "feat: enterprise Azure IaC, RBAC, CI/CD pipelines, and beginner docs" \
  --body "... (comprehensive PR description with all sections and checklist)"
```

**Result**: PR #5 updated at https://github.com/hanuman-dtech/Aastechsolution-invoice-app/pull/5

---

### Phase 14: What Happens Now (Automatically)

When the PR was pushed, GitHub Actions **automatically triggered** the `terraform-pr.yml` workflow:

```
PR #5 pushed
    │
    ▼
┌─── Job: quality-gates ─────────────────────────────────┐
│                                                         │
│  1. Checkout code                                       │
│  2. Setup Terraform 1.9.8                               │
│  3. Azure Login (OIDC — uses federated credential       │
│     with subject "pull_request")                        │
│  4. terraform fmt -check -recursive                     │
│     → Are all files formatted correctly?                │
│  5. terraform init + validate (dev and prod)            │
│     → Is the code syntactically valid?                  │
│  6. tflint                                              │
│     → Are there common mistakes?                        │
│  7. trivy IaC scan (HIGH/CRITICAL → fail)               │
│     → Are there security misconfigurations?             │
│                                                         │
└─────────────────────────────────────────────────────────┘
    │ (only if quality-gates passes)
    ▼
┌─── Job: plan (matrix: [dev, prod]) ────────────────────┐
│                                                         │
│  For each environment:                                  │
│  1. Azure Login (OIDC)                                  │
│  2. terraform init (with remote backend secrets)        │
│  3. terraform plan                                      │
│     → Shows exactly what WOULD be created               │
│  4. Upload plan artifact                                │
│     → Saved for audit trail (14 days)                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**After merge to main**, the `terraform-apply.yml` workflow will:

```
Merge to main
    │
    ▼
┌─── Job: apply-dev ─────────────────────────────────────┐
│  1. Azure Login (OIDC — subject "environment:dev")      │
│  2. terraform init                                      │
│  3. terraform apply -auto-approve                       │
│     → CREATES all dev resources in Azure                │
└─────────────────────────────────────────────────────────┘
    │ (only if dev succeeds)
    ▼
┌─── Job: apply-prod ────────────────────────────────────┐
│  ⏸️ PAUSED — waiting for reviewer approval              │
│     (hanuman-dtech must click "Approve" in GitHub UI)   │
│                                                         │
│  After approval:                                        │
│  1. Azure Login (OIDC — subject "environment:prod")     │
│  2. terraform init                                      │
│  3. terraform apply -auto-approve                       │
│     → CREATES all prod resources in Azure               │
└─────────────────────────────────────────────────────────┘
```

---

### Summary: Complete Execution Order

| # | Phase | Steps | Key Commands |
|---|-------|-------|-------------|
| 1 | Install Tools | 1-3 | `curl ... \| sudo bash`, `terraform --version` |
| 2 | Azure Login | 4-5 | `az login --use-device-code`, `az account show` |
| 3 | State Backend | 6-11 | `az provider register`, `az storage account create`, `az role assignment create`, `terraform init` |
| 4 | Terraform Code | 12-14 | Created 5 modules + 2 env configs, `terraform fmt`, `terraform validate` |
| 5 | CI/CD Pipelines | — | Created 5 workflow YAML files + dependabot.yml |
| 6 | Governance Docs | — | Created CODEOWNERS, ORG_DEVOPS_RULES.md, BRANCH_PROTECTION.md |
| 7 | OIDC Setup | 15-18 | `az ad app create`, `az ad sp create`, `az ad app federated-credential create` (×3) |
| 8 | SP Roles | 19-22 | `az role assignment create` (Contributor + UAA + Storage Blob) |
| 9 | GitHub Secrets | 23-24 | `gh secret set` (×6) |
| 10 | Environments | 25-27 | `gh api --method PUT .../environments/dev`, `.../environments/prod` |
| 11 | Branch Protection | 28 | `gh api --method PUT .../branches/main/protection` |
| 12 | .gitignore | 29 | Added `.env`, `backend.hcl` patterns |
| 13 | Commit & PR | 30-32 | `git commit`, `git push`, `gh pr edit` |
| 14 | Auto CI/CD | — | `terraform-pr.yml` triggers automatically on PR |

---

### Remaining Steps

| # | Task | How |
|---|------|-----|
| 1 | **Review & merge PR** | Approve PR #5 in GitHub, or temporarily disable `enforce_admins` to self-merge |
| 2 | **First `terraform apply`** | Triggered automatically when PR merges to main |
| 3 | **Create `terraform.tfvars`** | Copy from `.example`, fill in real subscription/tenant IDs for local testing |
| 4 | **Add Entra groups for RBAC** | Create groups in Entra ID, add their Object IDs to `terraform.tfvars` |
| 5 | **Rotate SMTP password** | Go to Apple ID > Sign-In & Security > App-Specific Passwords and revoke/recreate |

---

*Generated for the Aastechsolution Invoice App infrastructure. Last updated: March 2026.*
