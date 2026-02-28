"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import { getWeekdayLabel, formatDate } from "@/lib/utils";
import type { Customer, ScheduleConfig, ScheduleConfigUpdate } from "@/types";

export default function SchedulePage() {
  const queryClient = useQueryClient();

  const { data: customers, isLoading } = useQuery<Customer[]>({
    queryKey: ["customers-with-schedules"],
    queryFn: () => api.getCustomers({ active_only: true }),
  });

  const updateMutation = useMutation({
    mutationFn: ({
      customerId,
      data,
    }: {
      customerId: string;
      data: ScheduleConfigUpdate;
    }) => api.updateScheduleConfig(customerId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customers-with-schedules"] });
      toast.success("Schedule updated successfully");
    },
    onError: (error: Error) => {
      toast.error(`Failed to update schedule: ${error.message}`);
    },
  });

  const handleToggleEnabled = (customer: Customer) => {
    if (customer.schedule) {
      updateMutation.mutate({
        customerId: customer.id,
        data: { is_enabled: !customer.schedule.is_enabled },
      });
    }
  };

  const handleToggleAutoEmail = (customer: Customer) => {
    if (customer.schedule) {
      updateMutation.mutate({
        customerId: customer.id,
        data: { auto_send_email: !customer.schedule.auto_send_email },
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Schedule Configuration</h1>
        <p className="text-muted-foreground">
          Manage automatic invoice generation schedules for each customer
        </p>
      </div>

      {/* Schedule Table */}
      <Card>
        <CardHeader>
          <CardTitle>Customer Schedules</CardTitle>
          <CardDescription>
            Configure when invoices should be automatically generated
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading schedules...
            </div>
          ) : customers && customers.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Customer</TableHead>
                  <TableHead>Frequency</TableHead>
                  <TableHead>Billing Day</TableHead>
                  <TableHead>Anchor Date</TableHead>
                  <TableHead>Last Run</TableHead>
                  <TableHead>Next Run</TableHead>
                  <TableHead>Auto Email</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {customers.map((customer) => (
                  <TableRow key={customer.id}>
                    <TableCell className="font-medium">
                      {customer.name}
                    </TableCell>
                    <TableCell>
                      {customer.contract?.frequency ?? "-"}
                    </TableCell>
                    <TableCell>
                      {customer.schedule
                        ? getWeekdayLabel(customer.schedule.billing_weekday)
                        : "-"}
                    </TableCell>
                    <TableCell>
                      {customer.schedule?.anchor_date
                        ? formatDate(customer.schedule.anchor_date)
                        : "-"}
                    </TableCell>
                    <TableCell>
                      {customer.schedule?.last_run_date
                        ? formatDate(customer.schedule.last_run_date)
                        : "Never"}
                    </TableCell>
                    <TableCell>
                      {customer.schedule?.next_run_date
                        ? formatDate(customer.schedule.next_run_date)
                        : "-"}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant={
                          customer.schedule?.auto_send_email
                            ? "default"
                            : "outline"
                        }
                        size="sm"
                        onClick={() => handleToggleAutoEmail(customer)}
                        disabled={!customer.schedule || updateMutation.isPending}
                      >
                        {customer.schedule?.auto_send_email ? "ON" : "OFF"}
                      </Button>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant={
                          customer.schedule?.is_enabled
                            ? "default"
                            : "secondary"
                        }
                        size="sm"
                        onClick={() => handleToggleEnabled(customer)}
                        disabled={!customer.schedule || updateMutation.isPending}
                      >
                        {customer.schedule?.is_enabled
                          ? "Enabled"
                          : "Disabled"}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No customers with schedules found.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Schedule Info */}
      <Card>
        <CardHeader>
          <CardTitle>How Scheduling Works</CardTitle>
        </CardHeader>
        <CardContent className="prose dark:prose-invert max-w-none">
          <ul className="text-sm text-muted-foreground space-y-2">
            <li>
              <strong>Billing Weekday:</strong> The day of the week when invoices are generated (e.g., Friday)
            </li>
            <li>
              <strong>Anchor Date:</strong> A reference date used to calculate billing periods based on frequency
            </li>
            <li>
              <strong>Auto Email:</strong> When enabled, emails are automatically sent after invoice generation
            </li>
            <li>
              <strong>Scheduled runs</strong> can be triggered manually from the Generator page or run automatically via Celery Beat
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
