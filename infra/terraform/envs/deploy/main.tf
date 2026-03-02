# ─────────────────────────────────────────────────────────────
# Invoice Enterprise – Azure Deployment (Container Apps)
#
# All resources live in ONE resource group.
# Cleanup:  terraform destroy          (IaC)
#      or:  az group delete -n <rg>    (nuclear option)
# ─────────────────────────────────────────────────────────────

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

locals {
  suffix = random_string.suffix.result
  rg     = "rg-${var.name_prefix}-deploy-${local.suffix}"
  acr    = replace("acr${var.name_prefix}${local.suffix}", "-", "")
  pg     = "pg-${var.name_prefix}-${local.suffix}"
  law    = "law-${var.name_prefix}-${local.suffix}"
  cae    = "cae-${var.name_prefix}-${local.suffix}"

  # Derive a secret key if not provided
  secret_key = var.app_secret_key != "" ? var.app_secret_key : random_string.secret.result
}

resource "random_string" "secret" {
  length  = 64
  special = false
}

# ── Resource Group ──────────────────────────────────────────
resource "azurerm_resource_group" "this" {
  name     = local.rg
  location = var.location
  tags     = var.tags
}

# ── Container Registry (Basic – public, cheap) ─────────────
resource "azurerm_container_registry" "this" {
  name                          = local.acr
  resource_group_name           = azurerm_resource_group.this.name
  location                      = azurerm_resource_group.this.location
  sku                           = "Basic"
  admin_enabled                 = true
  public_network_access_enabled = true
  tags                          = var.tags
}

# ── PostgreSQL Flexible Server (Burstable B1ms ~$12/mo) ────
resource "azurerm_postgresql_flexible_server" "this" {
  name                          = local.pg
  resource_group_name           = azurerm_resource_group.this.name
  location                      = azurerm_resource_group.this.location
  version                       = "16"
  administrator_login           = var.db_admin_username
  administrator_password        = var.db_admin_password
  storage_mb                    = 32768
  sku_name                      = "B_Standard_B1ms"
  zone                          = "1"
  public_network_access_enabled = true
  tags                          = var.tags
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.this.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_postgresql_flexible_server_database" "this" {
  name      = "invoice_enterprise"
  server_id = azurerm_postgresql_flexible_server.this.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# ── Log Analytics (required for Container Apps Env) ─────────
resource "azurerm_log_analytics_workspace" "this" {
  name                = local.law
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

# ── Container Apps Environment ──────────────────────────────
resource "azurerm_container_app_environment" "this" {
  name                       = local.cae
  resource_group_name        = azurerm_resource_group.this.name
  location                   = azurerm_resource_group.this.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  tags                       = var.tags
}

# ── Redis (runs as a Container App – free inside the env) ──
resource "azurerm_container_app" "redis" {
  name                         = "redis"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"
  tags                         = var.tags

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "redis"
      image  = "redis:7-alpine"
      cpu    = 0.25
      memory = "0.5Gi"
    }
  }

  ingress {
    external_enabled = false
    target_port      = 6379
    transport        = "tcp"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

# ── Backend API ─────────────────────────────────────────────
resource "azurerm_container_app" "backend" {
  name                         = "invoice-backend"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"
  tags                         = var.tags

  registry {
    server               = azurerm_container_registry.this.login_server
    username             = azurerm_container_registry.this.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.this.admin_password
  }

  secret {
    name  = "db-url"
    value = "postgresql+asyncpg://${var.db_admin_username}:${var.db_admin_password}@${azurerm_postgresql_flexible_server.this.fqdn}:5432/invoice_enterprise?ssl=require"
  }

  secret {
    name  = "secret-key"
    value = local.secret_key
  }

  template {
    min_replicas = 1
    max_replicas = 3

    container {
      name   = "backend"
      image  = "${azurerm_container_registry.this.login_server}/invoice-backend:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "DATABASE_URL"
        secret_name = "db-url"
      }
      env {
        name  = "REDIS_URL"
        value = "redis://redis:6379/0"
      }
      env {
        name        = "SECRET_KEY"
        secret_name = "secret-key"
      }
      env {
        name  = "ENCRYPTION_KEY"
        value = substr(local.secret_key, 0, 32)
      }
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "DEBUG"
        value = "true"
      }
      env {
        name  = "CORS_ORIGINS"
        value = "[\"https://*\",\"http://*\"]"
      }
      env {
        name  = "SMTP_HOST"
        value = ""
      }
      env {
        name  = "SMTP_PORT"
        value = "587"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

# ── Celery Worker ───────────────────────────────────────────
resource "azurerm_container_app" "celery_worker" {
  name                         = "invoice-celery"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"
  tags                         = var.tags

  registry {
    server               = azurerm_container_registry.this.login_server
    username             = azurerm_container_registry.this.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.this.admin_password
  }

  secret {
    name  = "db-url"
    value = "postgresql+asyncpg://${var.db_admin_username}:${var.db_admin_password}@${azurerm_postgresql_flexible_server.this.fqdn}:5432/invoice_enterprise?ssl=require"
  }

  secret {
    name  = "secret-key"
    value = local.secret_key
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name    = "celery"
      image   = "${azurerm_container_registry.this.login_server}/invoice-backend:latest"
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["celery", "-A", "app.worker.tasks", "worker", "--loglevel=info"]

      env {
        name        = "DATABASE_URL"
        secret_name = "db-url"
      }
      env {
        name  = "REDIS_URL"
        value = "redis://redis:6379/0"
      }
      env {
        name        = "SECRET_KEY"
        secret_name = "secret-key"
      }
      env {
        name  = "ENCRYPTION_KEY"
        value = substr(local.secret_key, 0, 32)
      }
    }
  }
}

# ── Frontend ────────────────────────────────────────────────
resource "azurerm_container_app" "frontend" {
  name                         = "invoice-frontend"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"
  tags                         = var.tags

  registry {
    server               = azurerm_container_registry.this.login_server
    username             = azurerm_container_registry.this.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.this.admin_password
  }

  template {
    min_replicas = 1
    max_replicas = 3

    container {
      name   = "frontend"
      image  = "${azurerm_container_registry.this.login_server}/invoice-frontend:latest"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = "https://invoice-backend.${azurerm_container_app_environment.this.default_domain}"
      }
      env {
        name  = "NODE_ENV"
        value = "production"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 3000
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}
