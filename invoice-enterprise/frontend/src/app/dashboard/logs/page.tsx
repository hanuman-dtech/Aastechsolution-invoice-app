"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Clock, CheckCircle, XCircle, Filter } from "lucide-react";
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
import { formatDate, formatDateTime } from "@/lib/utils";
import type { ExecutionLog } from "@/types";

export default function LogsPage() {
  const [modeFilter, setModeFilter] = useState<string>("all");

  const { data: logs, isLoading } = useQuery<ExecutionLog[]>({
    queryKey: ["execution-logs", modeFilter],
    queryFn: () =>
      api.getExecutionLogs({
        mode: modeFilter !== "all" ? modeFilter : undefined,
        limit: 50,
      }),
  });

  const { data: stats } = useQuery({
    queryKey: ["execution-stats"],
    queryFn: () => api.getExecutionStats(),
  });

  const getModeColor = (mode: string) => {
    switch (mode) {
      case "quick":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400";
      case "wizard":
        return "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400";
      case "scheduled":
        return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400";
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Execution Logs</h1>
        <p className="text-muted-foreground">
          View history of all invoice generation runs
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_runs ?? "-"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Successful</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {stats?.successful_runs ?? "-"}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {stats?.failed_runs ?? "-"}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Last Run</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-sm font-medium">
              {stats?.last_run ? formatDateTime(stats.last_run) : "Never"}
            </div>
          </CardContent>
        </Card>
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
              <Select value={modeFilter} onValueChange={setModeFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Mode" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Modes</SelectItem>
                  <SelectItem value="quick">Quick</SelectItem>
                  <SelectItem value="wizard">Wizard</SelectItem>
                  <SelectItem value="scheduled">Scheduled</SelectItem>
                  <SelectItem value="manual">Manual Override</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card>
        <CardHeader>
          <CardTitle>Execution History</CardTitle>
          <CardDescription>
            {logs?.length ?? 0} logs found
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading logs...
            </div>
          ) : logs && logs.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Mode</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Customers</TableHead>
                  <TableHead>Matches</TableHead>
                  <TableHead>PDFs</TableHead>
                  <TableHead>Emails</TableHead>
                  <TableHead>Failures</TableHead>
                  <TableHead>Triggered By</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => {
                  const duration = log.completed_at
                    ? (
                        (new Date(log.completed_at).getTime() -
                          new Date(log.started_at).getTime()) /
                        1000
                      ).toFixed(2)
                    : "-";
                  return (
                    <TableRow key={log.id}>
                      <TableCell>{formatDate(log.run_date)}</TableCell>
                      <TableCell>
                        <Badge className={getModeColor(log.mode)}>
                          {log.mode}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatDateTime(log.started_at)}</TableCell>
                      <TableCell>{duration}s</TableCell>
                      <TableCell>{log.customers_loaded}</TableCell>
                      <TableCell>{log.schedule_matches}</TableCell>
                      <TableCell className="text-green-600">
                        {log.pdfs_generated}
                      </TableCell>
                      <TableCell className="text-blue-600">
                        {log.emails_sent}
                      </TableCell>
                      <TableCell
                        className={log.failures > 0 ? "text-red-600" : ""}
                      >
                        {log.failures}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {log.triggered_by || "-"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No execution logs found.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
