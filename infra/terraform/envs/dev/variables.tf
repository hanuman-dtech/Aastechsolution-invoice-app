variable "environment" {
  description = "Environment name."
  type        = string
  default     = "dev"
}

variable "subscription_id" {
  description = "Azure subscription ID."
  type        = string
}

variable "tenant_id" {
  description = "Azure tenant ID."
  type        = string
}

variable "location" {
  description = "Azure deployment region."
  type        = string
  default     = "canadacentral"
}

variable "name_prefix" {
  description = "Prefix used for resource naming."
  type        = string
  default     = "invoice"
}

variable "vnet_address_space" {
  description = "Address space for VNet."
  type        = list(string)
  default     = ["10.20.0.0/16"]
}

variable "app_subnet_prefixes" {
  description = "Address prefixes for app subnet."
  type        = list(string)
  default     = ["10.20.1.0/24"]
}

variable "private_endpoint_subnet_prefixes" {
  description = "Address prefixes for private endpoint subnet."
  type        = list(string)
  default     = ["10.20.2.0/24"]
}

variable "container_image" {
  description = "Container image path in ACR."
  type        = string
  default     = "invoice-api:latest"
}

variable "app_service_sku" {
  description = "App Service plan SKU."
  type        = string
  default     = "P1v3"
}

variable "log_analytics_local_authentication_enabled" {
  description = "Enable local authentication for Log Analytics workspace."
  type        = bool
  default     = true
}

variable "log_analytics_internet_ingestion_enabled" {
  description = "Allow internet ingestion for Log Analytics workspace. Keep false for strict private-only posture."
  type        = bool
  default     = false
}

variable "log_analytics_internet_query_enabled" {
  description = "Allow internet query for Log Analytics workspace. Keep false for strict private-only posture."
  type        = bool
  default     = false
}

variable "key_vault_admin_principal_ids" {
  description = "Extra Entra object IDs that should administer Key Vault via RBAC."
  type        = list(string)
  default     = []
}

variable "resource_group_contributor_principal_ids" {
  description = "Principal IDs (groups/SPs) with Contributor on the environment Resource Group."
  type        = list(string)
  default     = []
}

variable "resource_group_user_access_admin_principal_ids" {
  description = "Principal IDs (groups/SPs) with User Access Administrator on the environment Resource Group."
  type        = list(string)
  default     = []
}

variable "resource_group_reader_principal_ids" {
  description = "Principal IDs (groups/SPs) with Reader on the environment Resource Group."
  type        = list(string)
  default     = []
}

variable "security_reader_principal_ids" {
  description = "Principal IDs (groups/SPs) with Security Reader on the environment Resource Group."
  type        = list(string)
  default     = []
}

variable "log_analytics_reader_principal_ids" {
  description = "Principal IDs (groups/SPs) with Log Analytics Reader on the workspace."
  type        = list(string)
  default     = []
}

variable "acr_push_principal_ids" {
  description = "Principal IDs (groups/SPs) with AcrPush on ACR."
  type        = list(string)
  default     = []
}

variable "key_vault_secrets_officer_principal_ids" {
  description = "Principal IDs (groups/SPs) with Key Vault Secrets Officer on Key Vault."
  type        = list(string)
  default     = []
}

variable "app_service_contributor_principal_ids" {
  description = "Principal IDs (groups/SPs) with Website Contributor on App Service."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Base tags."
  type        = map(string)
  default = {
    project     = "invoice-enterprise"
    owner       = "platform-team"
    managed_by  = "terraform"
    cost_center = "engineering"
  }
}
