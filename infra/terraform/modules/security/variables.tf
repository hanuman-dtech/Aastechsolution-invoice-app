variable "resource_group_name" {
  description = "Target Resource Group name."
  type        = string
}

variable "location" {
  description = "Azure region for resources."
  type        = string
}

variable "acr_name" {
  description = "Azure Container Registry name (globally unique)."
  type        = string
}

variable "key_vault_name" {
  description = "Azure Key Vault name (globally unique)."
  type        = string
}

variable "tenant_id" {
  description = "Azure tenant ID for Key Vault."
  type        = string
}

variable "vnet_id" {
  description = "Virtual Network ID for Private DNS links."
  type        = string
}

variable "private_endpoint_subnet_id" {
  description = "Subnet ID used for private endpoints."
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID for diagnostics."
  type        = string
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}

variable "key_vault_rbac_principal_ids" {
  description = "Principal IDs granted Key Vault Administrator role."
  type        = list(string)
  default     = []
}

variable "acr_zone_redundancy_enabled" {
  description = "Enable zone redundancy for ACR (Premium only)."
  type        = bool
  default     = true
}
