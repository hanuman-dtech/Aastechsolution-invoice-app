locals {
  rg_contributors            = toset(var.resource_group_contributor_principal_ids)
  rg_user_access_admins      = toset(var.resource_group_user_access_admin_principal_ids)
  rg_readers                 = toset(var.resource_group_reader_principal_ids)
  rg_security_readers        = toset(var.security_reader_principal_ids)
  law_readers                = toset(var.log_analytics_reader_principal_ids)
  acr_pushers                = toset(var.acr_push_principal_ids)
  key_vault_secrets_officers = toset(var.key_vault_secrets_officer_principal_ids)
  app_service_contributors   = toset(var.app_service_contributor_principal_ids)
}

resource "azurerm_role_assignment" "rg_contributor" {
  for_each             = local.rg_contributors
  scope                = var.resource_group_id
  role_definition_name = "Contributor"
  principal_id         = each.value
}

resource "azurerm_role_assignment" "rg_user_access_admin" {
  for_each             = local.rg_user_access_admins
  scope                = var.resource_group_id
  role_definition_name = "User Access Administrator"
  principal_id         = each.value
}

resource "azurerm_role_assignment" "rg_reader" {
  for_each             = local.rg_readers
  scope                = var.resource_group_id
  role_definition_name = "Reader"
  principal_id         = each.value
}

resource "azurerm_role_assignment" "rg_security_reader" {
  for_each             = local.rg_security_readers
  scope                = var.resource_group_id
  role_definition_name = "Security Reader"
  principal_id         = each.value
}

resource "azurerm_role_assignment" "law_reader" {
  for_each             = local.law_readers
  scope                = var.log_analytics_workspace_id
  role_definition_name = "Log Analytics Reader"
  principal_id         = each.value
}

resource "azurerm_role_assignment" "acr_push" {
  for_each             = local.acr_pushers
  scope                = var.acr_id
  role_definition_name = "AcrPush"
  principal_id         = each.value
}

resource "azurerm_role_assignment" "kv_secrets_officer" {
  for_each             = local.key_vault_secrets_officers
  scope                = var.key_vault_id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = each.value
}

resource "azurerm_role_assignment" "app_service_contributor" {
  for_each             = local.app_service_contributors
  scope                = var.app_service_id
  role_definition_name = "Website Contributor"
  principal_id         = each.value
}
