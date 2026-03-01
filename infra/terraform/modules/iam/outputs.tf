output "role_assignment_counts" {
  description = "Counts of role assignments created by category."
  value = {
    rg_contributor          = length(azurerm_role_assignment.rg_contributor)
    rg_user_access_admin    = length(azurerm_role_assignment.rg_user_access_admin)
    rg_reader               = length(azurerm_role_assignment.rg_reader)
    rg_security_reader      = length(azurerm_role_assignment.rg_security_reader)
    law_reader              = length(azurerm_role_assignment.law_reader)
    acr_push                = length(azurerm_role_assignment.acr_push)
    kv_secrets_officer      = length(azurerm_role_assignment.kv_secrets_officer)
    app_service_contributor = length(azurerm_role_assignment.app_service_contributor)
  }
}
