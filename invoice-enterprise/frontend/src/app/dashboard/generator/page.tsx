"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Play, Zap, Calendar, Clock, CheckCircle, XCircle } from "lucide-react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/utils";
import type {
  Customer,
  QuickModeRequest,
  WizardModeRequest,
  ExecutionSummary,
} from "@/types";

type GenerationMode = "quick" | "wizard" | "scheduled";

export default function GeneratorPage() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<GenerationMode>("quick");
  const [selectedCustomer, setSelectedCustomer] = useState<string>("");
  const [result, setResult] = useState<ExecutionSummary | null>(null);
  const [showResult, setShowResult] = useState(false);

  // Form state for wizard mode
  const [wizardForm, setWizardForm] = useState({
    invoiceDate: new Date().toISOString().split("T")[0],
    periodStart: "",
    periodEnd: "",
    hours: "",
    rate: "",
    hstRate: "0.13",
    extraFees: "",
    extraFeesLabel: "",
    paymentTerms: "Monthly",
    sendEmail: false,
    allowDuplicate: false,
  });

  // Form state for quick mode
  const [quickForm, setQuickForm] = useState({
    runDate: new Date().toISOString().split("T")[0],
    hours: "",
    sendEmail: false,
  });

  // Scheduled mode state
  const [scheduledForm, setScheduledForm] = useState({
    runDate: new Date().toISOString().split("T")[0],
    autoSendEmail: false,
  });

  const { data: customers } = useQuery<Customer[]>({
    queryKey: ["customers"],
    queryFn: () => api.getCustomers({ active_only: true }),
  });

  const quickMutation = useMutation({
    mutationFn: (data: QuickModeRequest) => api.runQuickMode(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      setResult(data);
      setShowResult(true);
      toast.success(
        `Generated ${data.pdfs_generated} invoice(s) successfully`
      );
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail || error?.message || "Unknown error";
      toast.error(`Generation failed: ${detail}`);
    },
  });

  const wizardMutation = useMutation({
    mutationFn: (data: WizardModeRequest) => api.runWizardMode(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      setResult(data);
      setShowResult(true);
      toast.success(
        `Generated ${data.pdfs_generated} invoice(s) successfully`
      );
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail || error?.message || "Unknown error";
      toast.error(`Generation failed: ${detail}`);
    },
  });

  const scheduledMutation = useMutation({
    mutationFn: () =>
      api.runScheduled({
        run_date: scheduledForm.runDate,
        send_email: scheduledForm.autoSendEmail,
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      setResult(data);
      setShowResult(true);
      toast.success(
        `Processed ${data.customers_loaded} customers, generated ${data.pdfs_generated} invoices`
      );
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail || error?.message || "Unknown error";
      toast.error(`Scheduled run failed: ${detail}`);
    },
  });

  const handleQuickSubmit = () => {
    if (!selectedCustomer) {
      toast.error("Please select a customer");
      return;
    }
    if (!selectedCustomerData?.contract) {
      toast.error("Selected customer has no contract configured");
      return;
    }
    if (!quickForm.hours) {
      toast.error("Please enter total hours");
      return;
    }
    quickMutation.mutate({
      customer_id: selectedCustomer,
      run_date: quickForm.runDate,
      total_hours: parseFloat(quickForm.hours),
      send_email: quickForm.sendEmail,
    });
  };

  const handleWizardSubmit = () => {
    if (!selectedCustomer) {
      toast.error("Please select a customer");
      return;
    }
    if (!selectedCustomerData?.contract) {
      toast.error("Selected customer has no contract configured");
      return;
    }
    if (!wizardForm.periodStart || !wizardForm.periodEnd || !wizardForm.hours || !wizardForm.rate) {
      toast.error("Please fill in all required fields");
      return;
    }
    wizardMutation.mutate({
      customer_id: selectedCustomer,
      invoice_date: wizardForm.invoiceDate,
      period_start: wizardForm.periodStart,
      period_end: wizardForm.periodEnd,
      total_hours: parseFloat(wizardForm.hours),
      rate_per_hour: parseFloat(wizardForm.rate),
      hst_rate: wizardForm.hstRate ? parseFloat(wizardForm.hstRate) : 0.13,
      extra_fees: wizardForm.extraFees
        ? parseFloat(wizardForm.extraFees)
        : 0,
      extra_fees_label: wizardForm.extraFeesLabel || "Other Fees",
      payment_terms: wizardForm.paymentTerms || "Monthly",
      send_email: wizardForm.sendEmail,
      allow_duplicate: wizardForm.allowDuplicate,
    });
  };

  const isLoading =
    quickMutation.isPending ||
    wizardMutation.isPending ||
    scheduledMutation.isPending;

  const selectedCustomerData = customers?.find(
    (c) => c.id === selectedCustomer
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Invoice Generator</h1>
        <p className="text-muted-foreground">
          Generate invoices using different modes
        </p>
      </div>

      {/* Mode Selection */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card
          className={`cursor-pointer transition-colors ${
            mode === "quick" ? "border-primary bg-primary/5" : ""
          }`}
          onClick={() => setMode("quick")}
        >
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Quick Mode
            </CardTitle>
            <CardDescription>
              Generate invoice using contract defaults
            </CardDescription>
          </CardHeader>
        </Card>

        <Card
          className={`cursor-pointer transition-colors ${
            mode === "wizard" ? "border-primary bg-primary/5" : ""
          }`}
          onClick={() => setMode("wizard")}
        >
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Wizard Mode
            </CardTitle>
            <CardDescription>
              Full control over all invoice parameters
            </CardDescription>
          </CardHeader>
        </Card>

        <Card
          className={`cursor-pointer transition-colors ${
            mode === "scheduled" ? "border-primary bg-primary/5" : ""
          }`}
          onClick={() => setMode("scheduled")}
        >
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Scheduled Run
            </CardTitle>
            <CardDescription>
              Process all customers matching today&apos;s schedule
            </CardDescription>
          </CardHeader>
        </Card>
      </div>

      {/* Mode-specific Form */}
      {mode === "quick" && (
        <Card>
          <CardHeader>
            <CardTitle>Quick Invoice Generation</CardTitle>
            <CardDescription>
              Generate an invoice using the customer&apos;s contract settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Customer *</Label>
                <Select
                  value={selectedCustomer}
                  onValueChange={setSelectedCustomer}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select customer" />
                  </SelectTrigger>
                  <SelectContent>
                    {customers?.map((customer) => (
                      <SelectItem key={customer.id} value={customer.id}>
                        {customer.name}
                        {customer.contract && (
                          <span className="ml-2 text-muted-foreground">
                            ({customer.contract.invoice_prefix})
                          </span>
                        )}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Run Date *</Label>
                <Input
                  type="date"
                  required
                  value={quickForm.runDate}
                  onChange={(e) =>
                    setQuickForm({ ...quickForm, runDate: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Total Hours *</Label>
                <Input
                  type="number"
                  step="0.5"
                  required
                  placeholder={
                    selectedCustomerData?.contract
                      ? String(selectedCustomerData.contract.default_hours)
                      : "Hours"
                  }
                  value={quickForm.hours}
                  onChange={(e) =>
                    setQuickForm({ ...quickForm, hours: e.target.value })
                  }
                />
              </div>
              <div className="flex items-center space-x-2 pt-6">
                <input
                  type="checkbox"
                  id="quick-send-email"
                  checked={quickForm.sendEmail}
                  onChange={(e) =>
                    setQuickForm({ ...quickForm, sendEmail: e.target.checked })
                  }
                  className="h-4 w-4 rounded border-gray-300"
                />
                <Label htmlFor="quick-send-email">Send email after generation</Label>
              </div>
            </div>
            {selectedCustomerData?.contract && (
              <div className="rounded-lg bg-muted p-4">
                <h4 className="font-medium mb-2">Contract Preview</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    Rate: {formatCurrency(selectedCustomerData.contract.rate_per_hour)}/hr
                  </div>
                  <div>
                    Default Hours: {selectedCustomerData.contract.default_hours}
                  </div>
                  <div>HST: {(selectedCustomerData.contract.hst_rate * 100).toFixed(0)}%</div>
                  <div>
                    Frequency: {selectedCustomerData.contract.frequency}
                  </div>
                </div>
              </div>
            )}
            <Button
              onClick={handleQuickSubmit}
              disabled={!selectedCustomer || isLoading}
              className="w-full"
            >
              <Play className="mr-2 h-4 w-4" />
              {isLoading ? "Generating..." : "Generate Invoice"}
            </Button>
          </CardContent>
        </Card>
      )}

      {mode === "wizard" && (
        <Card>
          <CardHeader>
            <CardTitle>Wizard Mode - Full Control</CardTitle>
            <CardDescription>
              Specify all invoice parameters manually
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Customer</Label>
                <Select
                  value={selectedCustomer}
                  onValueChange={setSelectedCustomer}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select customer" />
                  </SelectTrigger>
                  <SelectContent>
                    {customers?.map((customer) => (
                      <SelectItem key={customer.id} value={customer.id}>
                        {customer.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Hours *</Label>
                <Input
                  type="number"
                  step="0.5"
                  required
                  value={wizardForm.hours}
                  onChange={(e) =>
                    setWizardForm({ ...wizardForm, hours: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Period Start *</Label>
                <Input
                  type="date"
                  required
                  value={wizardForm.periodStart}
                  onChange={(e) =>
                    setWizardForm({ ...wizardForm, periodStart: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>Period End *</Label>
                <Input
                  type="date"
                  required
                  value={wizardForm.periodEnd}
                  onChange={(e) =>
                    setWizardForm({ ...wizardForm, periodEnd: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Rate per Hour (optional)</Label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder={
                    selectedCustomerData?.contract
                      ? String(selectedCustomerData.contract.rate_per_hour)
                      : "Rate"
                  }
                  value={wizardForm.rate}
                  onChange={(e) =>
                    setWizardForm({ ...wizardForm, rate: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>Extra Fees (optional)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={wizardForm.extraFees}
                  onChange={(e) =>
                    setWizardForm({ ...wizardForm, extraFees: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Extra Fees Label</Label>
                <Input
                  placeholder="e.g., Cloud Services"
                  value={wizardForm.extraFeesLabel}
                  onChange={(e) =>
                    setWizardForm({
                      ...wizardForm,
                      extraFeesLabel: e.target.value,
                    })
                  }
                />
              </div>
              <div className="flex items-center space-x-2 pt-6">
                <input
                  type="checkbox"
                  id="wizard-send-email"
                  checked={wizardForm.sendEmail}
                  onChange={(e) =>
                    setWizardForm({ ...wizardForm, sendEmail: e.target.checked })
                  }
                  className="h-4 w-4 rounded border-gray-300"
                />
                <Label htmlFor="wizard-send-email">Send email after generation</Label>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="wizard-allow-duplicate"
                checked={wizardForm.allowDuplicate}
                onChange={(e) =>
                  setWizardForm({ ...wizardForm, allowDuplicate: e.target.checked })
                }
                className="h-4 w-4 rounded border-gray-300"
              />
              <Label htmlFor="wizard-allow-duplicate">
                Allow duplicate invoice for the same period (manual override)
              </Label>
            </div>
            <Button
              onClick={handleWizardSubmit}
              disabled={!selectedCustomer || isLoading}
              className="w-full"
            >
              <Play className="mr-2 h-4 w-4" />
              {isLoading ? "Generating..." : "Generate Invoice"}
            </Button>
          </CardContent>
        </Card>
      )}

      {mode === "scheduled" && (
        <Card>
          <CardHeader>
            <CardTitle>Scheduled Run</CardTitle>
            <CardDescription>
              Process all customers whose schedule matches the selected date
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Run Date</Label>
                <Input
                  type="date"
                  value={scheduledForm.runDate}
                  onChange={(e) =>
                    setScheduledForm({
                      ...scheduledForm,
                      runDate: e.target.value,
                    })
                  }
                />
              </div>
              <div className="flex items-center space-x-2 pt-6">
                <input
                  type="checkbox"
                  id="scheduled-send-email"
                  checked={scheduledForm.autoSendEmail}
                  onChange={(e) =>
                    setScheduledForm({
                      ...scheduledForm,
                      autoSendEmail: e.target.checked,
                    })
                  }
                  className="h-4 w-4 rounded border-gray-300"
                />
                <Label htmlFor="scheduled-send-email">
                  Auto-send emails (respects customer settings)
                </Label>
              </div>
            </div>
            <div className="rounded-lg bg-muted p-4">
              <h4 className="font-medium mb-2">What will happen:</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>1. Load all active customers with enabled schedules</li>
                <li>2. Check which customers match the billing schedule for {formatDate(scheduledForm.runDate)}</li>
                <li>3. Generate invoices for matching customers</li>
                <li>4. Optionally send emails based on customer settings</li>
              </ul>
            </div>
            <Button
              onClick={() => scheduledMutation.mutate()}
              disabled={isLoading}
              className="w-full"
            >
              <Play className="mr-2 h-4 w-4" />
              {isLoading ? "Processing..." : "Run Scheduled Generation"}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Result Dialog */}
      <Dialog open={showResult} onOpenChange={setShowResult}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {result && result.failures.length === 0 ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : (
                <XCircle className="h-5 w-5 text-red-500" />
              )}
              Generation Complete
            </DialogTitle>
            <DialogDescription>
              Execution summary for {result?.mode} mode
            </DialogDescription>
          </DialogHeader>
          {result && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-lg border p-4">
                  <div className="text-2xl font-bold text-green-600">
                    {result.pdfs_generated}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Invoices Generated
                  </div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-2xl font-bold text-blue-600">
                    {result.emails_sent}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Emails Sent
                  </div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-2xl font-bold">
                    {result.customers_loaded}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Customers Processed
                  </div>
                </div>
                <div className="rounded-lg border p-4">
                  <div
                    className={`text-2xl font-bold ${
                      result.failures.length > 0 ? "text-red-600" : "text-gray-600"
                    }`}
                  >
                    {result.failures.length}
                  </div>
                  <div className="text-sm text-muted-foreground">Failures</div>
                </div>
              </div>
              {result.generated_invoices.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Generated Invoices:</h4>
                  <div className="space-y-2">
                    {result.generated_invoices.map((inv) => (
                      <div
                        key={inv.id}
                        className="flex justify-between items-center rounded border p-2"
                      >
                        <span className="font-mono">{inv.invoice_number}</span>
                        <Badge>{inv.status}</Badge>
                        <span className="font-medium">
                          {formatCurrency(inv.total)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {result.failures.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2 text-red-600">Errors:</h4>
                  <ul className="text-sm text-red-600 space-y-1">
                    {result.failures.map((failure, i) => (
                      <li key={i}>
                        {failure.customer_name}: {failure.error}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="text-sm text-muted-foreground">
                Duration: {result.duration_seconds.toFixed(2)}s
              </div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setShowResult(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
