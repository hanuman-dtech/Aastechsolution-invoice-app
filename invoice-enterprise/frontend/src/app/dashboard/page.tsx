"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Users,
  FileText,
  DollarSign,
  TrendingUp,
  AlertCircle,
  Clock,
} from "lucide-react";
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
import { api } from "@/lib/api";
import { formatCurrency, formatDate, getStatusColor } from "@/lib/utils";
import type { DashboardStats, UpcomingInvoice, RecentActivity } from "@/types";

function StatsCard({
  title,
  value,
  description,
  icon: Icon,
  trend,
}: {
  title: string;
  value: string | number;
  description?: string;
  icon: React.ElementType;
  trend?: "up" | "down" | "neutral";
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboard-stats"],
    queryFn: () => api.getDashboardStats(),
  });

  const { data: upcoming, isLoading: upcomingLoading } = useQuery<UpcomingInvoice[]>({
    queryKey: ["upcoming-invoices"],
    queryFn: () => api.getUpcomingInvoices(14),
  });

  const { data: activity, isLoading: activityLoading } = useQuery<RecentActivity[]>({
    queryKey: ["recent-activity"],
    queryFn: () => api.getRecentActivity(5),
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your invoice operations
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Invoices This Month"
          value={stats?.total_invoices_this_month ?? "-"}
          description="Generated this month"
          icon={Users}
        />
        <StatsCard
          title="Revenue This Month"
          value={
            stats
              ? formatCurrency(Number(stats.total_revenue_this_month))
              : "-"
          }
          description="Current month total"
          icon={FileText}
        />
        <StatsCard
          title="Pending Emails"
          value={stats?.pending_emails ?? "-"}
          description="Awaiting send or retry"
          icon={DollarSign}
        />
        <StatsCard
          title="Scheduled (Upcoming)"
          value={stats?.upcoming_scheduled ?? "-"}
          description={
            stats?.last_run_date
              ? `Last run: ${formatDate(stats.last_run_date)}`
              : "No runs yet"
          }
          icon={stats?.last_run_status === "failed" ? AlertCircle : TrendingUp}
        />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Upcoming Invoices */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Upcoming Invoices
            </CardTitle>
            <CardDescription>
              Scheduled invoices for the next 14 days
            </CardDescription>
          </CardHeader>
          <CardContent>
            {upcomingLoading ? (
              <div className="text-center py-4 text-muted-foreground">
                Loading...
              </div>
            ) : upcoming && upcoming.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Customer</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-right">Est. Amount</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {upcoming.map((inv) => (
                    <TableRow key={inv.customer_id}>
                      <TableCell className="font-medium">
                        {inv.customer_name}
                      </TableCell>
                      <TableCell>{formatDate(inv.next_invoice_date)}</TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(inv.estimated_amount)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                No upcoming invoices
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest invoice operations</CardDescription>
          </CardHeader>
          <CardContent>
            {activityLoading ? (
              <div className="text-center py-4 text-muted-foreground">
                Loading...
              </div>
            ) : activity && activity.length > 0 ? (
              <div className="space-y-4">
                {activity.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-start gap-4 rounded-lg border p-3"
                  >
                    <div
                      className={`mt-1 h-2 w-2 rounded-full ${
                        item.failures === 0
                          ? "bg-green-500"
                          : "bg-red-500"
                      }`}
                    />
                    <div className="flex-1 space-y-1">
                      <p className="text-sm font-medium">
                        {item.mode.replace("_", " ")} run
                      </p>
                      <p className="text-xs text-muted-foreground">
                        PDFs: {item.pdfs_generated} · Emails: {item.emails_sent} · Failures: {item.failures}
                      </p>
                    </div>
                    <time className="text-xs text-muted-foreground">
                      {formatDate(item.started_at, "MMM d, h:mm a")}
                    </time>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                No recent activity
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
