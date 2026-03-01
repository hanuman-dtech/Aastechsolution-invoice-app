# Branch Protection & Approval Policy (Recommended)

Apply these settings on `main`:

1. **Require pull request before merging**
   - Require at least **2 approvals**
   - Dismiss stale approvals on new commits
   - Require review from code owners

2. **Require status checks to pass**
   - `terraform-pr / quality-gates`
   - `terraform-pr / plan (dev)`
   - `terraform-pr / plan (prod)`
   - `dependency-review / dependency-review`
   - `secret-scan / gitleaks`
   - `codeql / Analyze (python)`
   - `codeql / Analyze (javascript-typescript)`

3. **Require branches to be up to date before merge**

4. **Restrict who can push to main**
   - Only release managers / platform admins

5. **Require conversation resolution before merge**

6. **Require signed commits** (recommended for regulated environments)

7. **Enforce admins**

## Environment Protection

Configure GitHub Environments:

- `dev`: optional approval gate
- `prod`: required reviewers (minimum 2), wait timer optional (e.g., 10 minutes)

This ensures `terraform-apply` to production is human-approved even on `main`.
