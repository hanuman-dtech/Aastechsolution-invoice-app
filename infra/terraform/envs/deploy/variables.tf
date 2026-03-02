variable "subscription_id" {
  description = "Azure subscription ID."
  type        = string
}

variable "tenant_id" {
  description = "Azure tenant ID."
  type        = string
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "canadacentral"
}

variable "name_prefix" {
  description = "Prefix for resource naming."
  type        = string
  default     = "invoice"
}

variable "db_admin_username" {
  description = "PostgreSQL admin username."
  type        = string
  default     = "invoiceadmin"
}

variable "db_admin_password" {
  description = "PostgreSQL admin password."
  type        = string
  sensitive   = true
}

variable "app_secret_key" {
  description = "Secret key for the application."
  type        = string
  sensitive   = true
  default     = ""
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
  default = {
    project    = "invoice-enterprise"
    managed_by = "terraform"
  }
}
