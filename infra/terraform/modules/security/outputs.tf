output "acr_id" {
  description = "Azure Container Registry ID."
  value       = azurerm_container_registry.this.id
}

output "acr_login_server" {
  description = "Azure Container Registry login server."
  value       = azurerm_container_registry.this.login_server
}

output "key_vault_id" {
  description = "Key Vault ID."
  value       = azurerm_key_vault.this.id
}

output "key_vault_uri" {
  description = "Key Vault URI."
  value       = azurerm_key_vault.this.vault_uri
}
