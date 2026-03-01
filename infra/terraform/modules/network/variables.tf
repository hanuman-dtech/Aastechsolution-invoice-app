variable "name" {
  description = "Virtual Network name."
  type        = string
}

variable "resource_group_name" {
  description = "Target Resource Group name."
  type        = string
}

variable "location" {
  description = "Azure region for resources."
  type        = string
}

variable "address_space" {
  description = "Address space of the VNet."
  type        = list(string)
}

variable "subnets" {
  description = "Subnet definitions keyed by subnet name."
  type = map(object({
    address_prefixes                              = list(string)
    service_endpoints                             = optional(list(string), [])
    private_endpoint_network_policies_enabled     = optional(bool, false)
    private_link_service_network_policies_enabled = optional(bool, false)
    delegation = optional(object({
      name         = string
      service_name = string
      actions      = list(string)
    }))
  }))
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID for diagnostic settings."
  type        = string
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
