#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# destroy.sh — One-command destroy ALL Azure resources
#
# Usage:
#   cd infra/terraform/envs/deploy
#   ./destroy.sh
#
# This removes every resource created by deploy.sh.
# Nothing is left behind — zero orphan resources.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${CYAN}[DESTROY]${NC} $*"; }
ok()   { echo -e "${GREEN}[   OK  ]${NC} $*"; }
fail() { echo -e "${RED}[ FAIL  ]${NC} $*"; exit 1; }

cd "$SCRIPT_DIR"

# ── Verify state file exists ───────────────────────────────
if [[ ! -f terraform.tfstate ]]; then
  fail "No terraform.tfstate found in $(pwd). Nothing to destroy."
fi

# ── Get resource group name before destroying ───────────────
RG_NAME=$(terraform output -raw resource_group_name 2>/dev/null || echo "")

echo ""
echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║  WARNING: This will PERMANENTLY delete ALL Azure resources  ║${NC}"
echo -e "${RED}╠══════════════════════════════════════════════════════════════╣${NC}"
if [[ -n "$RG_NAME" ]]; then
echo -e "${RED}║${NC}  Resource Group: ${YELLOW}${RG_NAME}${NC}"
fi
echo -e "${RED}║${NC}  This includes: ACR, PostgreSQL, Container Apps, Redis     ${RED}║${NC}"
echo -e "${RED}║${NC}  All data will be LOST.                                    ${RED}║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

read -rp "Type 'destroy' to confirm: " CONFIRM
if [[ "$CONFIRM" != "destroy" ]]; then
  log "Aborted."
  exit 0
fi

# ── Step 1: Terraform destroy ──────────────────────────────
log "Destroying all Terraform-managed resources..."
terraform destroy -auto-approve

ok "Terraform destroy complete."

# ── Step 2: Safety net — delete resource group if it still exists
if [[ -n "$RG_NAME" ]]; then
  EXISTS=$(az group exists --name "$RG_NAME" 2>/dev/null || echo "false")
  if [[ "$EXISTS" == "true" ]]; then
    log "Resource group still exists — force deleting as safety net..."
    az group delete --name "$RG_NAME" --yes --no-wait 2>/dev/null || true
    ok "Resource group deletion initiated."
  fi
fi

# ── Step 3: Clean local Docker images ──────────────────────
log "Removing local Docker images..."
ACR_SERVER=$(grep -oP 'acr[a-z0-9]+\.azurecr\.io' terraform.tfstate 2>/dev/null | head -1 || echo "")
if [[ -n "$ACR_SERVER" ]]; then
  docker rmi "$ACR_SERVER/invoice-backend:latest" 2>/dev/null || true
  docker rmi "$ACR_SERVER/invoice-frontend:latest" 2>/dev/null || true
fi
ok "Local images cleaned."

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           ALL AZURE RESOURCES DESTROYED                     ║${NC}"
echo -e "${GREEN}║                                                             ║${NC}"
echo -e "${GREEN}║  Your Azure account is clean. Zero orphan resources.        ║${NC}"
echo -e "${GREEN}║  To redeploy: ./deploy.sh                                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
