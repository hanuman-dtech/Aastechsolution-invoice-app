# Azure Production-Grade Terraform + CI/CD Baseline

This folder contains an enterprise-ready Azure IaC foundation using Terraform with remote state, environment separation, private networking defaults, and GitHub Actions DevSecOps controls.

## Architecture Summary

- **Terraform latest-stable compatible** (`>= 1.7, < 2.0`) with `azurerm ~> 4.0`
- **Remote backend**: Azure Storage Blob (`azurerm` backend with state locking via blob lease)
- **Environments**: `dev`, `prod` (isolated state keys)
- **Modules**:
  - `modules/resource-group`
  - `modules/network`
  - `modules/security`
  - `modules/compute`
  - `modules/iam`
- **Security defaults**:
  - No public network access on ACR/Key Vault/Web App
  - Log Analytics internet ingestion/query disabled by default (private-first)
  - Private endpoints + private DNS
  - RBAC-based Key Vault access
  - Centralized least-privilege RBAC mappings per environment
  - Managed Identity for app and ACR pull
  - TLS enforced (`minimum_tls_version = 1.2`)
  - Soft-delete and purge protection on Key Vault
- **Observability**: Log Analytics + diagnostic settings on managed resources

## Folder Structure

```text
infra/terraform/
├── README.md
├── modules/
│   ├── compute/
│   │   ├── main.tf
│   │   ├── outputs.tf
│   │   └── variables.tf
│   ├── network/
│   │   ├── main.tf
│   │   ├── outputs.tf
│   │   └── variables.tf
│   ├── resource-group/
│   │   ├── main.tf
│   │   ├── outputs.tf
│   │   └── variables.tf
│   └── security/
│       ├── main.tf
│       ├── outputs.tf
│       └── variables.tf
│   └── iam/
│       ├── main.tf
│       ├── outputs.tf
│       └── variables.tf
└── envs/
    ├── dev/
    │   ├── backend.hcl.example
    │   ├── main.tf
    │   ├── outputs.tf
    │   ├── providers.tf
    │   ├── terraform.tfvars.example
    │   ├── variables.tf
    │   └── versions.tf
    └── prod/
        ├── backend.hcl.example
        ├── main.tf
        ├── outputs.tf
        ├── providers.tf
        ├── terraform.tfvars.example
        ├── variables.tf
        └── versions.tf
```

## Prerequisites

- Terraform 1.7+
- Azure CLI 2.60+
- An Azure subscription
- GitHub repository admin rights (for environments and branch protection)

## One-Time Azure OIDC Setup (No Client Secret)

1. **Create Entra application + service principal**:
   - Register an app in Entra ID (App registrations).
   - Create service principal for it.

2. **Add federated credentials** on the app:
   - Credential 1 (PR/plan for dev):
     - Issuer: `https://token.actions.githubusercontent.com`
     - Subject: `repo:<OWNER>/<REPO>:environment:dev`
     - Audience: `api://AzureADTokenExchange`
   - Credential 2 (apply for prod):
     - Subject: `repo:<OWNER>/<REPO>:environment:prod`

3. **Grant least privilege on Azure**:
   - Scope: target subscription or management group
   - Roles (minimum):
     - `Contributor` (or tighter custom role for Terraform-managed resources)
     - `User Access Administrator` (if Terraform creates RBAC assignments)

4. **Create remote state resources** (once):
   - Resource group for state
   - Storage account (with secure settings)
   - Blob container (e.g., `tfstate`)

5. **Set GitHub repository secrets**:
   - `AZURE_CLIENT_ID`
   - `AZURE_TENANT_ID`
   - `AZURE_SUBSCRIPTION_ID`
   - `TFSTATE_RESOURCE_GROUP`
   - `TFSTATE_STORAGE_ACCOUNT`
   - `TFSTATE_CONTAINER`

6. **Create GitHub Environments**:
   - `dev` (optional reviewer gate)
   - `prod` (**required reviewers enabled**)

## Local Usage

From repo root:

1. Copy examples:
   - `infra/terraform/envs/dev/backend.hcl.example` -> `infra/terraform/envs/dev/backend.hcl`
   - `infra/terraform/envs/dev/terraform.tfvars.example` -> `infra/terraform/envs/dev/terraform.tfvars`
   - same for `prod`

2. Initialize and plan dev:
   - `terraform -chdir=infra/terraform/envs/dev init -backend-config=backend.hcl`
   - `terraform -chdir=infra/terraform/envs/dev plan -var-file=terraform.tfvars`

3. Apply dev:
   - `terraform -chdir=infra/terraform/envs/dev apply -var-file=terraform.tfvars`

4. Repeat for prod with stricter approvals/change control.

## GitHub Actions Workflows

- `terraform-pr.yml`
  - `fmt`, `validate`, `tflint`, `trivy` IaC scan
  - Fails on `HIGH/CRITICAL`
  - Generates `terraform plan` for dev/prod
  - Uploads plan artifacts

- `terraform-apply.yml`
  - Applies on `main`
  - `dev` first, then `prod` with environment protection gates

- `codeql.yml`
  - Code scanning for Python + JavaScript/TypeScript

- `dependency-review.yml`
  - Blocks high-risk dependency changes on PR

- `secret-scan.yml`
  - Gitleaks-based secret detection

## Notes on Zero-Trust Posture

- App ingress is private by default (private endpoint)
- Registry and vault are private-only
- Log Analytics defaults to private-only network posture; internet ingestion/query can be explicitly enabled per environment variable when required
- No static secrets required for Azure authentication in CI/CD (OIDC)
- Managed identity is used for runtime resource access

## Enterprise RBAC Model

Use Entra group object IDs (not user IDs) in `terraform.tfvars` to enforce enterprise, auditable access boundaries:

- `resource_group_contributor_principal_ids`: platform engineers who deploy infra
- `resource_group_user_access_admin_principal_ids`: tightly controlled IAM admins
- `resource_group_reader_principal_ids`: read-only operations/support
- `security_reader_principal_ids`: security/compliance teams
- `log_analytics_reader_principal_ids`: observability/SOC teams
- `acr_push_principal_ids`: CI build identities that publish images
- `key_vault_secrets_officer_principal_ids`: secrets operations team
- `app_service_contributor_principal_ids`: application operations team

Recommended org rule: all privileged role assignments must be via groups managed by identity governance/PIM, with no direct user assignments.

## Branch Protection Guidance

See `.github/BRANCH_PROTECTION.md` for recommended protected branch policy and required checks.

See `.github/ORG_DEVOPS_RULES.md` for enterprise DevSecOps governance controls.
