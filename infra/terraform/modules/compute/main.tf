resource "azurerm_service_plan" "this" {
  name                = var.service_plan_name
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.sku_name
  tags                = var.tags
}

resource "azurerm_linux_web_app" "this" {
  name                      = var.app_name
  resource_group_name       = var.resource_group_name
  location                  = var.location
  service_plan_id           = azurerm_service_plan.this.id
  virtual_network_subnet_id = var.app_subnet_id

  https_only                    = true
  public_network_access_enabled = false
  tags                          = var.tags

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on                               = true
    minimum_tls_version                     = "1.2"
    ftps_state                              = "Disabled"
    health_check_path                       = var.health_check_path
    vnet_route_all_enabled                  = true
    container_registry_use_managed_identity = true

    application_stack {
      docker_registry_url = "https://${var.acr_login_server}"
      docker_image_name   = var.container_image
    }
  }

  app_settings = merge(
    {
      WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
      WEBSITES_PORT                       = "8000"
      DOCKER_REGISTRY_SERVER_URL          = "https://${var.acr_login_server}"
      KEY_VAULT_URI                       = var.key_vault_uri
    },
    var.app_settings
  )
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_linux_web_app.this.identity[0].principal_id
}

resource "azurerm_role_assignment" "key_vault_secrets_user" {
  scope                = var.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_web_app.this.identity[0].principal_id
}

resource "azurerm_private_dns_zone" "appservice" {
  name                = "privatelink.azurewebsites.net"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "appservice" {
  name                  = "vnetlink-webapp"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.appservice.name
  virtual_network_id    = var.vnet_id
  registration_enabled  = false
  tags                  = var.tags
}

resource "azurerm_private_endpoint" "appservice" {
  name                = "pep-${var.app_name}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.private_endpoint_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-${var.app_name}"
    private_connection_resource_id = azurerm_linux_web_app.this.id
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "pdzg-webapp"
    private_dns_zone_ids = [azurerm_private_dns_zone.appservice.id]
  }
}

data "azurerm_monitor_diagnostic_categories" "service_plan" {
  resource_id = azurerm_service_plan.this.id
}

resource "azurerm_monitor_diagnostic_setting" "service_plan" {
  name                       = "diag-${azurerm_service_plan.this.name}"
  target_resource_id         = azurerm_service_plan.this.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  dynamic "enabled_log" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.service_plan.log_category_types)
    content {
      category = enabled_log.value
    }
  }

  dynamic "enabled_metric" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.service_plan.metrics)
    content {
      category = enabled_metric.value
    }
  }
}

data "azurerm_monitor_diagnostic_categories" "web_app" {
  resource_id = azurerm_linux_web_app.this.id
}

resource "azurerm_monitor_diagnostic_setting" "web_app" {
  name                       = "diag-${azurerm_linux_web_app.this.name}"
  target_resource_id         = azurerm_linux_web_app.this.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  dynamic "enabled_log" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.web_app.log_category_types)
    content {
      category = enabled_log.value
    }
  }

  dynamic "enabled_metric" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.web_app.metrics)
    content {
      category = enabled_metric.value
    }
  }
}


