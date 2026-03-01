output "resource_group_name" {
  value       = module.resource_group.name
  description = "Resource Group name."
}

output "log_analytics_workspace_id" {
  value       = azurerm_log_analytics_workspace.this.id
  description = "Log Analytics Workspace ID."
}

output "acr_login_server" {
  value       = module.security.acr_login_server
  description = "ACR login server for CI image pushes."
}

output "app_service_name" {
  value       = module.compute.app_name
  description = "App Service name."
}

output "key_vault_uri" {
  value       = module.security.key_vault_uri
  description = "Key Vault URI."
}
