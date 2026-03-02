#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# deploy.sh — One-command deploy of Invoice Enterprise to Azure
#
# Usage:
#   cd infra/terraform/envs/deploy
#   ./deploy.sh
#
# Prerequisites: az cli (logged in), terraform, docker
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${CYAN}[DEPLOY]${NC} $*"; }
ok()   { echo -e "${GREEN}[  OK  ]${NC} $*"; }
warn() { echo -e "${YELLOW}[ WARN ]${NC} $*"; }
fail() { echo -e "${RED}[FAIL ]${NC} $*"; exit 1; }

# ── Pre-flight checks ──────────────────────────────────────
log "Running pre-flight checks..."

command -v az        >/dev/null 2>&1 || fail "Azure CLI not found. Install: https://aka.ms/installazurecli"
command -v terraform >/dev/null 2>&1 || fail "Terraform not found. Install: https://developer.hashicorp.com/terraform/install"
command -v docker    >/dev/null 2>&1 || fail "Docker not found. Install: https://docs.docker.com/get-docker/"

az account show >/dev/null 2>&1 || fail "Not logged in to Azure. Run: az login"
docker info     >/dev/null 2>&1 || fail "Docker daemon not running. Start Docker Desktop."

ok "All tools found and authenticated."

# ── Ensure terraform.tfvars exists ──────────────────────────
cd "$SCRIPT_DIR"

if [[ ! -f terraform.tfvars ]]; then
  log "No terraform.tfvars found. Creating from your Azure CLI context..."
  SUB_ID=$(az account show --query id -o tsv)
  TENANT_ID=$(az account show --query tenantId -o tsv)

  read -rsp "Enter PostgreSQL admin password (min 8 chars, mixed case + digits): " DB_PASS
  echo

  cat > terraform.tfvars <<EOF
subscription_id   = "$SUB_ID"
tenant_id         = "$TENANT_ID"
db_admin_username = "invoiceadmin"
db_admin_password = "$DB_PASS"
EOF
  ok "Created terraform.tfvars"
fi

# ── Register required Azure providers ───────────────────────
log "Ensuring required Azure resource providers are registered..."
for provider in Microsoft.App Microsoft.ContainerRegistry Microsoft.DBforPostgreSQL Microsoft.OperationalInsights; do
  STATE=$(az provider show -n "$provider" --query "registrationState" -o tsv 2>/dev/null || echo "NotRegistered")
  if [[ "$STATE" != "Registered" ]]; then
    az provider register --namespace "$provider" --wait >/dev/null 2>&1 &
    log "  Registering $provider (background)..."
  fi
done
wait
ok "All resource providers registered."

# ── Step 1: Terraform init ──────────────────────────────────
log "Step 1/5 — Terraform init..."
terraform init -input=false -upgrade >/dev/null 2>&1
ok "Terraform initialized."

# ── Step 2: Create infra (ACR, PostgreSQL, etc.) ────────────
log "Step 2/5 — Creating Azure infrastructure (ACR, PostgreSQL, Log Analytics, Container Apps Environment)..."
terraform apply -input=false -auto-approve \
  -target=azurerm_resource_group.this \
  -target=azurerm_container_registry.this \
  -target=azurerm_postgresql_flexible_server.this \
  -target=azurerm_postgresql_flexible_server_firewall_rule.allow_azure \
  -target=azurerm_postgresql_flexible_server_database.this \
  -target=azurerm_log_analytics_workspace.this \
  -target=azurerm_container_app_environment.this \
  -target=azurerm_container_app.redis \
  -target=random_string.suffix \
  -target=random_string.secret

ok "Base infrastructure created."

# ── Step 3: Build & push Docker images to ACR ───────────────
ACR_SERVER=$(terraform output -raw acr_login_server)
log "Step 3/5 — Building & pushing Docker images to $ACR_SERVER..."

# Login to ACR
az acr login --name "${ACR_SERVER%%.*}" >/dev/null 2>&1
ok "Logged in to ACR."

# Build + push backend
log "  Building backend image..."
docker build -t "$ACR_SERVER/invoice-backend:latest" \
  -f "$REPO_ROOT/invoice-enterprise/backend/Dockerfile" \
  --target production \
  "$REPO_ROOT/invoice-enterprise/backend" --quiet
docker push "$ACR_SERVER/invoice-backend:latest" --quiet
ok "  Backend image pushed."

# Build + push frontend
log "  Building frontend image..."
docker build -t "$ACR_SERVER/invoice-frontend:latest" \
  -f "$REPO_ROOT/invoice-enterprise/frontend/Dockerfile" \
  --target production \
  "$REPO_ROOT/invoice-enterprise/frontend" --quiet
docker push "$ACR_SERVER/invoice-frontend:latest" --quiet
ok "  Frontend image pushed."

# ── Step 4: Deploy Container Apps ───────────────────────────
log "Step 4/5 — Deploying Container Apps (backend, celery, frontend)..."
terraform apply -input=false -auto-approve
ok "All Container Apps deployed."

# ── Step 5: Verify health ──────────────────────────────────
BACKEND_URL=$(terraform output -raw backend_url)
FRONTEND_URL=$(terraform output -raw frontend_url)

log "Step 5/5 — Verifying health..."
sleep 15  # give containers time to start

HEALTH=$(curl -sf "${BACKEND_URL}/health" 2>/dev/null || echo "FAIL")
if echo "$HEALTH" | grep -q '"healthy"'; then
  ok "Backend is healthy."
else
  warn "Backend health check failed — it may need a few more seconds to start."
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            DEPLOYMENT COMPLETE                             ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC} Frontend:  ${CYAN}${FRONTEND_URL}${NC}"
echo -e "${GREEN}║${NC} Backend:   ${CYAN}${BACKEND_URL}${NC}"
echo -e "${GREEN}║${NC} API Docs:  ${CYAN}${BACKEND_URL}/api/docs${NC}"
echo -e "${GREEN}║${NC} Health:    ${CYAN}${BACKEND_URL}/health${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC} To destroy: ${YELLOW}./destroy.sh${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
