resource "azurerm_virtual_network" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = var.address_space
  tags                = var.tags
}

resource "azurerm_subnet" "this" {
  for_each = var.subnets

  name                                          = each.key
  resource_group_name                           = var.resource_group_name
  virtual_network_name                          = azurerm_virtual_network.this.name
  address_prefixes                              = each.value.address_prefixes
  service_endpoints                             = each.value.service_endpoints
  private_endpoint_network_policies             = each.value.private_endpoint_network_policies_enabled ? "Enabled" : "Disabled"
  private_link_service_network_policies_enabled = each.value.private_link_service_network_policies_enabled

  dynamic "delegation" {
    for_each = each.value.delegation == null ? [] : [each.value.delegation]
    content {
      name = delegation.value.name

      service_delegation {
        name    = delegation.value.service_name
        actions = delegation.value.actions
      }
    }
  }
}

data "azurerm_monitor_diagnostic_categories" "vnet" {
  resource_id = azurerm_virtual_network.this.id
}

resource "azurerm_monitor_diagnostic_setting" "vnet" {
  name                       = "diag-${azurerm_virtual_network.this.name}"
  target_resource_id         = azurerm_virtual_network.this.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  dynamic "enabled_log" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.vnet.log_category_types)
    content {
      category = enabled_log.value
    }
  }

  dynamic "metric" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.vnet.metrics)
    content {
      category = metric.value
      enabled  = true
    }
  }
}

data "azurerm_monitor_diagnostic_categories" "subnet" {
  for_each    = azurerm_subnet.this
  resource_id = each.value.id
}

resource "azurerm_monitor_diagnostic_setting" "subnet" {
  for_each = azurerm_subnet.this

  name                       = "diag-${each.value.name}"
  target_resource_id         = each.value.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  dynamic "enabled_log" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.subnet[each.key].log_category_types)
    content {
      category = enabled_log.value
    }
  }

  dynamic "metric" {
    for_each = toset(data.azurerm_monitor_diagnostic_categories.subnet[each.key].metrics)
    content {
      category = metric.value
      enabled  = true
    }
  }
}
