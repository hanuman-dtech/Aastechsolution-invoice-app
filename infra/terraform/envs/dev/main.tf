resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

locals {
  env_suffix = lower(var.environment)
  suffix     = random_string.suffix.result

  common_tags = merge(var.tags, {
    environment = var.environment
  })

  resource_group_name   = "rg-${var.name_prefix}-${local.env_suffix}"
  vnet_name             = "vnet-${var.name_prefix}-${local.env_suffix}"
  log_analytics_name    = "law-${var.name_prefix}-${local.env_suffix}-${local.suffix}"
  acr_name              = substr(replace("acr${var.name_prefix}${local.env_suffix}${local.suffix}", "-", ""), 0, 50)
  key_vault_name        = substr(replace("kv-${var.name_prefix}-${local.env_suffix}-${local.suffix}", "_", "-"), 0, 24)
  app_service_plan_name = "asp-${var.name_prefix}-${local.env_suffix}"
  app_name              = substr(replace("app-${var.name_prefix}-${local.env_suffix}-${local.suffix}", "_", "-"), 0, 60)
}

module "resource_group" {
  source = "../../modules/resource-group"

  name     = local.resource_group_name
  location = var.location
  tags     = local.common_tags
}

resource "azurerm_log_analytics_workspace" "this" {
  name                         = local.log_analytics_name
  resource_group_name          = module.resource_group.name
  location                     = module.resource_group.location
  sku                          = "PerGB2018"
  retention_in_days            = 30
  local_authentication_enabled = var.log_analytics_local_authentication_enabled
  internet_ingestion_enabled   = var.log_analytics_internet_ingestion_enabled
  internet_query_enabled       = var.log_analytics_internet_query_enabled
  tags                         = local.common_tags
}

module "network" {
  source = "../../modules/network"

  name                       = local.vnet_name
  resource_group_name        = module.resource_group.name
  location                   = module.resource_group.location
  address_space              = var.vnet_address_space
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  tags                       = local.common_tags

  subnets = {
    app = {
      address_prefixes = var.app_subnet_prefixes
      delegation = {
        name         = "appsvc-delegation"
        service_name = "Microsoft.Web/serverFarms"
        actions      = ["Microsoft.Network/virtualNetworks/subnets/action"]
      }
    }
    private-endpoints = {
      address_prefixes = var.private_endpoint_subnet_prefixes
    }
  }
}

module "security" {
  source = "../../modules/security"

  resource_group_name          = module.resource_group.name
  location                     = module.resource_group.location
  acr_name                     = local.acr_name
  key_vault_name               = local.key_vault_name
  tenant_id                    = var.tenant_id
  vnet_id                      = module.network.vnet_id
  private_endpoint_subnet_id   = module.network.subnet_ids["private-endpoints"]
  log_analytics_workspace_id   = azurerm_log_analytics_workspace.this.id
  key_vault_rbac_principal_ids = distinct(concat([data.azurerm_client_config.current.object_id], var.key_vault_admin_principal_ids))
  acr_zone_redundancy_enabled  = false
  tags                         = local.common_tags
}

module "compute" {
  source = "../../modules/compute"

  resource_group_name        = module.resource_group.name
  location                   = module.resource_group.location
  service_plan_name          = local.app_service_plan_name
  app_name                   = local.app_name
  acr_id                     = module.security.acr_id
  acr_login_server           = module.security.acr_login_server
  container_image            = var.container_image
  key_vault_id               = module.security.key_vault_id
  key_vault_uri              = module.security.key_vault_uri
  vnet_id                    = module.network.vnet_id
  app_subnet_id              = module.network.subnet_ids["app"]
  private_endpoint_subnet_id = module.network.subnet_ids["private-endpoints"]
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  sku_name                   = var.app_service_sku
  app_settings = {
    APP_ENV = var.environment
  }
  tags = local.common_tags
}

module "iam" {
  source = "../../modules/iam"

  resource_group_id                              = module.resource_group.id
  acr_id                                         = module.security.acr_id
  key_vault_id                                   = module.security.key_vault_id
  log_analytics_workspace_id                     = azurerm_log_analytics_workspace.this.id
  app_service_id                                 = module.compute.app_id
  resource_group_contributor_principal_ids       = var.resource_group_contributor_principal_ids
  resource_group_user_access_admin_principal_ids = var.resource_group_user_access_admin_principal_ids
  resource_group_reader_principal_ids            = var.resource_group_reader_principal_ids
  security_reader_principal_ids                  = var.security_reader_principal_ids
  log_analytics_reader_principal_ids             = var.log_analytics_reader_principal_ids
  acr_push_principal_ids                         = var.acr_push_principal_ids
  key_vault_secrets_officer_principal_ids        = var.key_vault_secrets_officer_principal_ids
  app_service_contributor_principal_ids          = var.app_service_contributor_principal_ids
}


