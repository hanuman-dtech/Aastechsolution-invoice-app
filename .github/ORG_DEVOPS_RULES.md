# Enterprise DevOps & RBAC Guardrails

This document defines organization-level controls for this repository.

## Identity and Access (RBAC)

1. Use Entra groups for all Terraform role assignments. Avoid direct user assignments.
2. Use least privilege:
   - `Contributor` only for platform deploy groups
   - `User Access Administrator` only for IAM admin groups
   - `Reader` / `Security Reader` / `Log Analytics Reader` for observer personas
3. Use workload identities (OIDC) for CI/CD; prohibit client secrets for pipeline auth.
4. Enforce emergency (break-glass) accounts outside daily operations and monitor usage.

## Branch and Environment Protection

1. Protect `main` branch:
   - minimum 2 approvals
   - code-owner review required
   - stale approvals dismissed on new commits
   - conversations must be resolved
2. Require checks before merge:
   - terraform-pr quality gates
   - terraform plans for dev/prod
   - secret scan
   - dependency review
   - CodeQL (Python + JS/TS)
3. Environment approvals:
   - `prod` must require at least 2 reviewers
   - apply to prod only through protected environment

## CI/CD Security Rules

1. Pin action versions to major versions or commit SHAs based on org policy.
2. Use least-privilege workflow permissions (job-level overrides when needed).
3. Fail builds on HIGH/CRITICAL IaC findings.
4. Upload Terraform plan artifacts for audit traceability.
5. Keep dependency updates automated via Dependabot.

## Terraform Operational Rules

1. Remote state only; no local state files in source control.
2. Separate state and variables by environment.
3. Require `terraform fmt`, `validate`, `tflint`, and IaC scanning in PRs.
4. Use private endpoints and disable public access unless explicitly approved.
5. Enable diagnostics and centralize logs in Log Analytics.

## Secrets and Data Protection

1. Never store credentials/secrets in repository files.
2. Rotate leaked credentials immediately and purge from git history.
3. Use Key Vault + Managed Identity for runtime secret access.

## Change Management

1. All infrastructure changes must be pull-request based.
2. Production applies must be approved and auditable.
3. Incident rollback plans must be documented for prod-impacting changes.
