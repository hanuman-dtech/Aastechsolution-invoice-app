variable "resource_group_id" {
  description = "Resource Group ID scope for org-level role assignments."
  type        = string
}

variable "acr_id" {
  description = "Azure Container Registry ID for image push access assignments."
  type        = string
}

variable "key_vault_id" {
  description = "Key Vault ID for secrets access assignments."
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID for read/operations assignments."
  type        = string
}

variable "app_service_id" {
  description = "App Service ID for app operations role assignments."
  type        = string
}

variable "resource_group_contributor_principal_ids" {
  description = "Principal IDs (groups/SPs) that can manage resources in the RG."
  type        = list(string)
  default     = []
}

variable "resource_group_user_access_admin_principal_ids" {
  description = "Principal IDs allowed to manage RBAC assignments in the RG."
  type        = list(string)
  default     = []
}

variable "resource_group_reader_principal_ids" {
  description = "Principal IDs with read-only access to the RG."
  type        = list(string)
  default     = []
}

variable "security_reader_principal_ids" {
  description = "Principal IDs for Security Reader at RG scope."
  type        = list(string)
  default     = []
}

variable "log_analytics_reader_principal_ids" {
  description = "Principal IDs with Log Analytics Reader permissions."
  type        = list(string)
  default     = []
}

variable "acr_push_principal_ids" {
  description = "Principal IDs allowed to push images to ACR."
  type        = list(string)
  default     = []
}

variable "key_vault_secrets_officer_principal_ids" {
  description = "Principal IDs allowed to manage secrets in Key Vault."
  type        = list(string)
  default     = []
}

variable "app_service_contributor_principal_ids" {
  description = "Principal IDs allowed to operate App Service configuration/deployments."
  type        = list(string)
  default     = []
}
