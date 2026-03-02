output "resource_group_name" {
  description = "Resource group name — delete this to clean up everything."
  value       = azurerm_resource_group.this.name
}

output "acr_login_server" {
  description = "ACR login server for Docker push."
  value       = azurerm_container_registry.this.login_server
}

output "backend_url" {
  description = "Backend API URL."
  value       = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
}

output "frontend_url" {
  description = "Frontend URL."
  value       = "https://${azurerm_container_app.frontend.ingress[0].fqdn}"
}

output "postgres_fqdn" {
  description = "PostgreSQL server FQDN."
  value       = azurerm_postgresql_flexible_server.this.fqdn
}

output "cleanup_command" {
  description = "Run this to destroy everything."
  value       = "cd infra/terraform/envs/deploy && terraform destroy -auto-approve"
}
