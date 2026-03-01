// API Types matching backend schemas

export type BillingFrequency = "weekly" | "biweekly" | "monthly";
export type InvoiceStatus = "generated" | "sent" | "failed";
export type EmailStatus = "pending" | "sent" | "failed";
export type ExecutionMode = "quick" | "wizard" | "scheduled" | "manual_override";
export type UserRole = "admin" | "operator" | "viewer";

// Base types
export interface BaseEntity {
  id: string;
  created_at: string;
  updated_at: string;
}

// User
export interface User extends BaseEntity {
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  last_login: string | null;
}

// Vendor
export interface Vendor extends BaseEntity {
  name: string;
  email: string;
  address_line1: string;
  address_line2: string | null;
  city: string;
  province: string;
  postal_code: string;
  country: string;
  hst_number: string;
  default_contractor: string;
  is_active: boolean;
}

export interface VendorCreate {
  name: string;
  email: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  province: string;
  postal_code: string;
  country?: string;
  hst_number: string;
  default_contractor: string;
}

export interface VendorUpdate extends Partial<VendorCreate> {
  is_active?: boolean;
}

// Customer
export interface Customer extends BaseEntity {
  vendor_id: string;
  name: string;
  email: string;
  address_line1: string;
  address_line2: string | null;
  city: string;
  province: string;
  postal_code: string;
  country: string;
  contractor_name: string;
  service_location: string;
  is_active: boolean;
  contract?: Contract;
  schedule?: ScheduleConfig;
}

export interface CustomerCreate {
  vendor_id: string;
  name: string;
  email: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  province: string;
  postal_code: string;
  country?: string;
  contractor_name: string;
  service_location?: string;
  payment_terms?: string;
}

export interface CustomerUpdate extends Partial<CustomerCreate> {
  is_active?: boolean;
}

// Contract
export interface Contract extends BaseEntity {
  customer_id: string;
  invoice_prefix: string;
  frequency: BillingFrequency;
  default_hours: number;
  rate_per_hour: number;
  hst_rate: number;
  payment_terms: string;
  extra_fees: number;
  extra_fees_label: string;
  notes: string | null;
  is_active: boolean;
}

export interface ContractCreate {
  customer_id: string;
  invoice_prefix: string;
  frequency?: BillingFrequency;
  default_hours?: number;
  rate_per_hour: number;
  hst_rate?: number;
  payment_terms?: string;
  extra_fees?: number;
  extra_fees_label?: string;
  notes?: string;
}

export interface ContractUpdate extends Partial<Omit<ContractCreate, "customer_id">> {
  is_active?: boolean;
}

// Schedule Config
export interface ScheduleConfig extends BaseEntity {
  customer_id: string;
  is_enabled: boolean;
  auto_send_email: boolean;
  timezone: string;
  billing_weekday: number;
  anchor_date: string;
  billing_day: number;
  last_run_date: string | null;
  next_run_date: string | null;
}

export interface ScheduleConfigCreate {
  customer_id: string;
  is_enabled?: boolean;
  auto_send_email?: boolean;
  timezone?: string;
  billing_weekday?: number;
  anchor_date?: string;
  billing_day?: number;
}

export interface ScheduleConfigUpdate extends Partial<Omit<ScheduleConfigCreate, "customer_id">> {}

// Invoice
export interface Invoice extends BaseEntity {
  customer_id: string;
  invoice_number: string;
  invoice_date: string;
  period_start: string;
  period_end: string;
  status: InvoiceStatus;
  total_hours: number;
  rate_per_hour: number;
  labor_subtotal: number;
  extra_fees: number;
  extra_fees_label: string;
  subtotal: number;
  hst_rate: number;
  hst_amount: number;
  total: number;
  pdf_path: string | null;
  generation_mode: ExecutionMode;
  customer?: Customer;
  lines?: InvoiceLine[];
  email_logs?: EmailLog[];
}

export interface InvoiceLine extends BaseEntity {
  invoice_id: string;
  description: string;
  quantity: number;
  unit_price: number;
  line_total: number;
  sort_order: number;
}

// Email Log
export interface EmailLog extends BaseEntity {
  invoice_id: string;
  recipient_email: string;
  subject: string;
  status: EmailStatus;
  error_message: string | null;
  sent_at: string | null;
  retry_count: number;
}

// Execution Log
export interface ExecutionLog extends BaseEntity {
  run_date: string;
  mode: ExecutionMode;
  started_at: string;
  completed_at: string | null;
  customers_loaded: number;
  schedule_matches: number;
  pdfs_generated: number;
  emails_sent: number;
  failures: number;
  error_trace: string | null;
  request_id: string | null;
  triggered_by: string | null;
}

// SMTP Config
export interface SmtpConfig extends BaseEntity {
  vendor_id: string | null;
  name: string;
  host: string;
  port: number;
  username: string;
  from_email: string;
  from_name: string | null;
  use_tls: boolean;
  is_active: boolean;
}

export interface SmtpConfigCreate {
  vendor_id?: string;
  name: string;
  host: string;
  port?: number;
  username: string;
  password: string;
  from_email: string;
  from_name?: string;
  use_tls?: boolean;
}

export interface SmtpConfigUpdate extends Partial<Omit<SmtpConfigCreate, "password">> {
  password?: string;
  is_active?: boolean;
}

// Invoice Generation Requests
export interface QuickModeRequest {
  customer_id: string;
  run_date: string;
  total_hours: number;
  send_email?: boolean;
}

export interface WizardModeRequest {
  customer_id: string;
  invoice_date: string;
  period_start: string;
  period_end: string;
  total_hours: number;
  rate_per_hour: number;
  hst_rate?: number;
  extra_fees?: number;
  extra_fees_label?: string;
  payment_terms?: string;
  send_email?: boolean;
  allow_duplicate?: boolean;
}

export interface ScheduledRunRequest {
  run_date: string;
  ignore_schedule?: boolean;
  send_email?: boolean;
  customer_ids?: string[];
}

export interface ManualDateOverrideRequest {
  customer_id: string;
  invoice_date: string;
  period_start: string;
  period_end: string;
  hours?: number;
  send_email?: boolean;
}

// Execution Summary Response
export interface ExecutionSummary {
  execution_id: string;
  mode: ExecutionMode;
  run_date: string;
  customers_loaded: number;
  schedule_matches: number;
  pdfs_generated: number;
  emails_sent: number;
  emails_failed: number;
  failures: Array<{
    customer_id: string;
    customer_name: string;
    error: string;
  }>;
  generated_invoices: Invoice[];
  download_links: string[];
  duration_seconds: number;
}

// Dashboard Types
export interface DashboardStats {
  total_customers: number;
  active_customers: number;
  total_invoices: number;
  total_revenue: number;
  invoices_this_month: number;
  revenue_this_month: number;
  pending_emails: number;
  recent_failures: number;
}

export interface UpcomingInvoice {
  customer_id: string;
  customer_name: string;
  next_invoice_date: string;
  estimated_amount: number;
  frequency: BillingFrequency;
}

export interface RecentActivity {
  id: string;
  type: "invoice" | "email" | "execution";
  title: string;
  description: string;
  timestamp: string;
  status: "success" | "warning" | "error";
}

export interface RevenueByMonth {
  month: string;
  revenue: number;
  invoices: number;
}

// API Response Types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
}

// Table Column Types
export interface ColumnSort {
  id: string;
  desc: boolean;
}

export interface TableState {
  sorting: ColumnSort[];
  pageIndex: number;
  pageSize: number;
}

// Form Types
export interface SelectOption {
  value: string;
  label: string;
}

export const FREQUENCY_OPTIONS: SelectOption[] = [
  { value: "weekly", label: "Weekly" },
  { value: "biweekly", label: "Bi-Weekly" },
  { value: "monthly", label: "Monthly" },
];

export const WEEKDAY_OPTIONS: SelectOption[] = [
  { value: "0", label: "Monday" },
  { value: "1", label: "Tuesday" },
  { value: "2", label: "Wednesday" },
  { value: "3", label: "Thursday" },
  { value: "4", label: "Friday" },
  { value: "5", label: "Saturday" },
  { value: "6", label: "Sunday" },
];

export const STATUS_OPTIONS: SelectOption[] = [
  { value: "generated", label: "Generated" },
  { value: "sent", label: "Sent" },
  { value: "failed", label: "Failed" },
];

export const CANADIAN_PROVINCES: SelectOption[] = [
  { value: "AB", label: "Alberta" },
  { value: "BC", label: "British Columbia" },
  { value: "MB", label: "Manitoba" },
  { value: "NB", label: "New Brunswick" },
  { value: "NL", label: "Newfoundland and Labrador" },
  { value: "NS", label: "Nova Scotia" },
  { value: "NT", label: "Northwest Territories" },
  { value: "NU", label: "Nunavut" },
  { value: "ON", label: "Ontario" },
  { value: "PE", label: "Prince Edward Island" },
  { value: "QC", label: "Quebec" },
  { value: "SK", label: "Saskatchewan" },
  { value: "YT", label: "Yukon" },
];
