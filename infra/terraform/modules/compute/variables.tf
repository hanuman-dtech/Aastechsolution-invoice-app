variable "resource_group_name" {
  description = "Target Resource Group name."
  type        = string
}

variable "location" {
  description = "Azure region for resources."
  type        = string
}

variable "service_plan_name" {
  description = "App Service Plan name."
  type        = string
}

variable "app_name" {
  description = "Linux Web App name (globally unique)."
  type        = string
}

variable "acr_id" {
  description = "Azure Container Registry resource ID."
  type        = string
}

variable "acr_login_server" {
  description = "Azure Container Registry login server."
  type        = string
}

variable "container_image" {
  description = "Container image in ACR to run in App Service."
  type        = string
}

variable "key_vault_id" {
  description = "Key Vault resource ID."
  type        = string
}

variable "key_vault_uri" {
  description = "Key Vault URI."
  type        = string
}

variable "vnet_id" {
  description = "VNet ID for Private DNS link."
  type        = string
}

variable "app_subnet_id" {
  description = "Subnet ID used for web app VNet integration."
  type        = string
}

variable "private_endpoint_subnet_id" {
  description = "Subnet ID used for private endpoint."
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID for diagnostics."
  type        = string
}

variable "health_check_path" {
  description = "Web app health check path."
  type        = string
  default     = "/health"
}

variable "sku_name" {
  description = "App Service Plan SKU."
  type        = string
  default     = "P1v3"
}

variable "app_settings" {
  description = "Additional application settings."
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
