resource "azurerm_container_registry" "this" {
  name                          = var.acr_name
  resource_group_name           = var.resource_group_name
  location                      = var.location
  sku                           = "Premium"
  admin_enabled                 = false
  public_network_access_enabled = false
  zone_redundancy_enabled       = var.acr_zone_redundancy_enabled
  tags                          = var.tags
}

resource "azurerm_key_vault" "this" {
  name                          = var.key_vault_name
  resource_group_name           = var.resource_group_name
  location                      = var.location
  tenant_id                     = var.tenant_id
  sku_name                      = "premium"
  rbac_authorization_enabled    = true
  public_network_access_enabled = false
  purge_protection_enabled      = true
  soft_delete_retention_days    = 90
  tags                          = var.tags

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
  }
}

resource "azurerm_role_assignment" "key_vault_admin" {
  for_each             = toset(var.key_vault_rbac_principal_ids)
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = each.value
}

resource "azurerm_private_dns_zone" "acr" {
  name                = "privatelink.azurecr.io"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "acr" {
  name                  = "vnetlink-acr"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.acr.name
  virtual_network_id    = var.vnet_id
  registration_enabled  = false
  tags                  = var.tags
}

resource "azurerm_private_endpoint" "acr" {
  name                = "pep-${var.acr_name}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.private_endpoint_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-${var.acr_name}"
    private_connection_resource_id = azurerm_container_registry.this.id
    subresource_names              = ["registry"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "pdzg-acr"
    private_dns_zone_ids = [azurerm_private_dns_zone.acr.id]
  }
}

resource "azurerm_private_dns_zone" "kv" {
  name                = "privatelink.vaultcore.azure.net"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "kv" {
  name                  = "vnetlink-kv"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.kv.name
  virtual_network_id    = var.vnet_id
  registration_enabled  = false
  tags                  = var.tags
}

resource "azurerm_private_endpoint" "kv" {
  name                = "pep-${var.key_vault_name}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.private_endpoint_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-${var.key_vault_name}"
    private_connection_resource_id = azurerm_key_vault.this.id
    subresource_names              = ["vault"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "pdzg-kv"
    private_dns_zone_ids = [azurerm_private_dns_zone.kv.id]
  }
}

data "azurerm_monitor_diagnostic_categories" "acr" {
  resource_id = azurerm_container_registry.this.id
}

resource "azurerm_monitor_diagnostic_setting" "acr" {
  name                       = "diag-${azurerm_container_registry.this.name}"
  target_resource_id         = azurerm_container_registry.this.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  dynamic "enabled_log" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.acr.log_category_types)
    content {
      category = enabled_log.value
    }
  }

  dynamic "metric" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.acr.metrics)
    content {
      category = metric.value
      enabled  = true
    }
  }
}

data "azurerm_monitor_diagnostic_categories" "kv" {
  resource_id = azurerm_key_vault.this.id
}

resource "azurerm_monitor_diagnostic_setting" "kv" {
  name                       = "diag-${azurerm_key_vault.this.name}"
  target_resource_id         = azurerm_key_vault.this.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  dynamic "enabled_log" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.kv.log_category_types)
    content {
      category = enabled_log.value
    }
  }

  dynamic "metric" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.kv.metrics)
    content {
      category = metric.value
      enabled  = true
    }
  }
}

data "azurerm_monitor_diagnostic_categories" "private_endpoint" {
  for_each = {
    acr = azurerm_private_endpoint.acr.id
    kv  = azurerm_private_endpoint.kv.id
  }
  resource_id = each.value
}

resource "azurerm_monitor_diagnostic_setting" "private_endpoint" {
  for_each = {
    acr = azurerm_private_endpoint.acr.id
    kv  = azurerm_private_endpoint.kv.id
  }

  name                       = "diag-${split("/", each.value)[8]}"
  target_resource_id         = each.value
  log_analytics_workspace_id = var.log_analytics_workspace_id

  dynamic "enabled_log" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.private_endpoint[each.key].log_category_types)
    content {
      category = enabled_log.value
    }
  }

  dynamic "metric" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.private_endpoint[each.key].metrics)
    content {
      category = metric.value
      enabled  = true
    }
  }
}

data "azurerm_monitor_diagnostic_categories" "private_dns_zone" {
  for_each = {
    acr = azurerm_private_dns_zone.acr.id
    kv  = azurerm_private_dns_zone.kv.id
  }
  resource_id = each.value
}

resource "azurerm_monitor_diagnostic_setting" "private_dns_zone" {
  for_each = {
    acr = azurerm_private_dns_zone.acr.id
    kv  = azurerm_private_dns_zone.kv.id
  }

  name                       = "diag-${split("/", each.value)[8]}"
  target_resource_id         = each.value
  log_analytics_workspace_id = var.log_analytics_workspace_id

  dynamic "enabled_log" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.private_dns_zone[each.key].log_category_types)
    content {
      category = enabled_log.value
    }
  }

  dynamic "metric" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.private_dns_zone[each.key].metrics)
    content {
      category = metric.value
      enabled  = true
    }
  }
}
