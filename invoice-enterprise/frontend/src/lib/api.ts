import axios, { AxiosError, AxiosInstance } from "axios";
import type {
  Customer,
  CustomerCreate,
  CustomerUpdate,
  Contract,
  ContractCreate,
  ContractUpdate,
  ScheduleConfig,
  ScheduleConfigCreate,
  ScheduleConfigUpdate,
  Invoice,
  Vendor,
  VendorCreate,
  VendorUpdate,
  SmtpConfig,
  SmtpConfigCreate,
  SmtpConfigUpdate,
  ExecutionLog,
  DashboardStats,
  UpcomingInvoice,
  RecentActivity,
  RevenueByMonth,
  QuickModeRequest,
  WizardModeRequest,
  ScheduledRunRequest,
  ManualDateOverrideRequest,
  ExecutionSummary,
  PaginatedResponse,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api`,
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Handle unauthorized - redirect to login
          window.location.href = "/login";
        }
        return Promise.reject(error);
      }
    );
  }

  setAuthToken(token: string) {
    this.client.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  }

  clearAuthToken() {
    delete this.client.defaults.headers.common["Authorization"];
  }

  // Dashboard
  async getDashboardStats(): Promise<DashboardStats> {
    const { data } = await this.client.get("/dashboard/stats");
    return data;
  }

  async getUpcomingInvoices(days = 14): Promise<UpcomingInvoice[]> {
    const { data } = await this.client.get(`/dashboard/upcoming?days=${days}`);
    return data;
  }

  async getRecentActivity(limit = 10): Promise<RecentActivity[]> {
    const { data } = await this.client.get(`/dashboard/activity?limit=${limit}`);
    return data;
  }

  async getRevenueByMonth(months = 6): Promise<RevenueByMonth[]> {
    const { data } = await this.client.get(`/dashboard/revenue?months=${months}`);
    return data;
  }

  // Vendors
  async getVendors(): Promise<Vendor[]> {
    const { data } = await this.client.get("/vendors");
    return data;
  }

  async getVendor(id: string): Promise<Vendor> {
    const { data } = await this.client.get(`/vendors/${id}`);
    return data;
  }

  async createVendor(vendor: VendorCreate): Promise<Vendor> {
    const { data } = await this.client.post("/vendors", vendor);
    return data;
  }

  async updateVendor(id: string, vendor: VendorUpdate): Promise<Vendor> {
    const { data } = await this.client.patch(`/vendors/${id}`, vendor);
    return data;
  }

  async deleteVendor(id: string): Promise<void> {
    await this.client.delete(`/vendors/${id}`);
  }

  // Customers
  async getCustomers(params?: {
    vendor_id?: string;
    active_only?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<Customer[]> {
    const { data } = await this.client.get("/customers", { params });
    return data;
  }

  async getCustomer(id: string): Promise<Customer> {
    const { data } = await this.client.get(`/customers/${id}`);
    return data;
  }

  async createCustomer(customer: CustomerCreate): Promise<Customer> {
    const { data } = await this.client.post("/customers", customer);
    return data;
  }

  async updateCustomer(id: string, customer: CustomerUpdate): Promise<Customer> {
    const { data } = await this.client.patch(`/customers/${id}`, customer);
    return data;
  }

  async deleteCustomer(id: string): Promise<void> {
    await this.client.delete(`/customers/${id}`);
  }

  // Contracts
  async getContract(customerId: string): Promise<Contract> {
    const { data } = await this.client.get(`/customers/${customerId}/contract`);
    return data;
  }

  async createContract(contract: ContractCreate): Promise<Contract> {
    const { data } = await this.client.post(
      `/customers/${contract.customer_id}/contract`,
      contract
    );
    return data;
  }

  async updateContract(customerId: string, contract: ContractUpdate): Promise<Contract> {
    const { data } = await this.client.patch(
      `/customers/${customerId}/contract`,
      contract
    );
    return data;
  }

  // Schedule Configs
  async getScheduleConfig(customerId: string): Promise<ScheduleConfig> {
    const { data } = await this.client.get(`/customers/${customerId}/schedule`);
    return data;
  }

  async createScheduleConfig(config: ScheduleConfigCreate): Promise<ScheduleConfig> {
    const { data } = await this.client.post(
      `/customers/${config.customer_id}/schedule`,
      config
    );
    return data;
  }

  async updateScheduleConfig(
    customerId: string,
    config: ScheduleConfigUpdate
  ): Promise<ScheduleConfig> {
    const { data } = await this.client.patch(
      `/customers/${customerId}/schedule`,
      config
    );
    return data;
  }

  async getNextInvoicePreview(customerId: string): Promise<{
    next_invoice_date: string;
    period_start: string;
    period_end: string;
    estimated_hours: number;
    estimated_amount: number;
  }> {
    const { data } = await this.client.get(`/customers/${customerId}/next-invoice`);
    return data;
  }

  // Invoices
  async getInvoices(params?: {
    customer_id?: string;
    status?: string;
    start_date?: string;
    end_date?: string;
    skip?: number;
    limit?: number;
  }): Promise<Invoice[]> {
    const { data } = await this.client.get("/invoices", { params });
    return data.items ?? [];
  }

  async getInvoice(id: string): Promise<Invoice> {
    const { data } = await this.client.get(`/invoices/${id}`);
    return data;
  }

  async downloadInvoicePdf(id: string): Promise<Blob> {
    const { data } = await this.client.get(`/invoices/${id}/download`, {
      responseType: "blob",
    });
    return data;
  }

  async resendInvoiceEmail(id: string): Promise<{ message: string }> {
    const { data } = await this.client.post(`/invoices/${id}/resend-email`);
    return data;
  }

  // Invoice Generation
  async runQuickMode(request: QuickModeRequest): Promise<ExecutionSummary> {
    const { data } = await this.client.post("/invoices/run/quick", request);
    return data;
  }

  async runWizardMode(request: WizardModeRequest): Promise<ExecutionSummary> {
    const { data } = await this.client.post("/invoices/run/wizard", request);
    return data;
  }

  async runScheduled(request?: ScheduledRunRequest): Promise<ExecutionSummary> {
    const { data } = await this.client.post("/invoices/run/scheduled", request || {});
    return data;
  }

  async runManualOverride(request: ManualDateOverrideRequest): Promise<ExecutionSummary> {
    const { data } = await this.client.post("/invoices/run/manual", request);
    return data;
  }

  // SMTP Config
  async getSmtpConfigs(): Promise<SmtpConfig[]> {
    const { data } = await this.client.get("/smtp-configs");
    return data;
  }

  async getSmtpConfig(id: string): Promise<SmtpConfig> {
    const { data } = await this.client.get(`/smtp-configs/${id}`);
    return data;
  }

  async createSmtpConfig(config: SmtpConfigCreate): Promise<SmtpConfig> {
    const { data } = await this.client.post("/smtp-configs", config);
    return data;
  }

  async updateSmtpConfig(id: string, config: SmtpConfigUpdate): Promise<SmtpConfig> {
    const { data } = await this.client.patch(`/smtp-configs/${id}`, config);
    return data;
  }

  async deleteSmtpConfig(id: string): Promise<void> {
    await this.client.delete(`/smtp-configs/${id}`);
  }

  async testSmtpConnection(
    id: string,
    testEmail: string
  ): Promise<{ success: boolean; message: string }> {
    const { data } = await this.client.post(`/smtp-configs/${id}/test`, null, {
      params: { test_email: testEmail },
    });
    return data;
  }

  // Execution Logs
  async getExecutionLogs(params?: {
    mode?: string;
    start_date?: string;
    end_date?: string;
    skip?: number;
    limit?: number;
  }): Promise<ExecutionLog[]> {
    const { data } = await this.client.get("/logs", { params });
    return data;
  }

  async getExecutionStats(): Promise<{
    total_runs: number;
    successful_runs: number;
    failed_runs: number;
    last_run: string | null;
  }> {
    const { data } = await this.client.get("/logs/stats");
    return data;
  }
}

export const api = new ApiClient();
