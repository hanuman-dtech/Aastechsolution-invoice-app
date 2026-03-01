output "app_id" {
  description = "App Service resource ID."
  value       = azurerm_linux_web_app.this.id
}

output "app_name" {
  description = "App Service name."
  value       = azurerm_linux_web_app.this.name
}

output "principal_id" {
  description = "Managed Identity principal ID of the app."
  value       = azurerm_linux_web_app.this.identity[0].principal_id
}
