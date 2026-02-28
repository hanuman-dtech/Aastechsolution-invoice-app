"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, Mail, Eye, Filter } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import {
  formatCurrency,
  formatDate,
  getStatusColor,
  downloadFile,
} from "@/lib/utils";
import type { Invoice, Customer } from "@/types";

export default function InvoicesPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [customerFilter, setCustomerFilter] = useState<string>("all");

  const { data: invoices, isLoading } = useQuery<Invoice[]>({
    queryKey: ["invoices", statusFilter, customerFilter],
    queryFn: () =>
      api.getInvoices({
        status: statusFilter !== "all" ? statusFilter : undefined,
        customer_id: customerFilter !== "all" ? customerFilter : undefined,
      }),
  });

  const { data: customers } = useQuery<Customer[]>({
    queryKey: ["customers"],
    queryFn: () => api.getCustomers(),
  });

  const customerNameById = Object.fromEntries(
    (customers ?? []).map((customer) => [customer.id, customer.name])
  ) as Record<string, string>;

  const downloadMutation = useMutation({
    mutationFn: async (invoice: Invoice) => {
      const blob = await api.downloadInvoicePdf(invoice.id);
      downloadFile(blob, `${invoice.invoice_number}.pdf`);
    },
    onError: (error: Error) => {
      toast.error(`Failed to download: ${error.message}`);
    },
  });

  const resendMutation = useMutation({
    mutationFn: (id: string) => api.resendInvoiceEmail(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      toast.success("Email queued for sending");
    },
    onError: (error: Error) => {
      toast.error(`Failed to resend email: ${error.message}`);
    },
  });

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case "sent":
        return "success";
      case "failed":
        return "destructive";
      default:
        return "warning";
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Invoices</h1>
        <p className="text-muted-foreground">
          View and manage all generated invoices
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="w-48">
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="generated">Generated</SelectItem>
                  <SelectItem value="sent">Sent</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-64">
              <Select value={customerFilter} onValueChange={setCustomerFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Customer" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Customers</SelectItem>
                  {customers?.map((customer) => (
                    <SelectItem key={customer.id} value={customer.id}>
                      {customer.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Invoices Table */}
      <Card>
        <CardHeader>
          <CardTitle>Invoice History</CardTitle>
          <CardDescription>
            {invoices?.length ?? 0} invoices found
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading invoices...
            </div>
          ) : invoices && invoices.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Invoice #</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Hours</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices.map((invoice) => (
                  <TableRow key={invoice.id}>
                    <TableCell className="font-medium font-mono">
                      {invoice.invoice_number}
                    </TableCell>
                    <TableCell>
                      {invoice.customer?.name ?? customerNameById[invoice.customer_id] ?? "Unknown"}
                    </TableCell>
                    <TableCell>{formatDate(invoice.invoice_date)}</TableCell>
                    <TableCell>
                      {formatDate(invoice.period_start)} -{" "}
                      {formatDate(invoice.period_end)}
                    </TableCell>
                    <TableCell>{invoice.total_hours}</TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrency(invoice.total)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={getStatusBadgeVariant(invoice.status)}>
                        {invoice.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => downloadMutation.mutate(invoice)}
                          disabled={downloadMutation.isPending}
                          title="Download PDF"
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => resendMutation.mutate(invoice.id)}
                          disabled={resendMutation.isPending}
                          title="Resend Email"
                        >
                          <Mail className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No invoices found matching your filters.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
