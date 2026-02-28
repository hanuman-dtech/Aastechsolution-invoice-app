"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, TestTube, CheckCircle, XCircle } from "lucide-react";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import type { SmtpConfig, SmtpConfigCreate, SmtpConfigUpdate } from "@/types";

export default function EmailConfigPage() {
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<SmtpConfig | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);

  const { data: configs, isLoading } = useQuery<SmtpConfig[]>({
    queryKey: ["smtp-configs"],
    queryFn: () => api.getSmtpConfigs(),
  });

  const createMutation = useMutation({
    mutationFn: (data: SmtpConfigCreate) => api.createSmtpConfig(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["smtp-configs"] });
      setIsCreateOpen(false);
      toast.success("SMTP configuration created successfully");
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail || error?.message || "Unknown error";
      toast.error(`Failed to create SMTP config: ${detail}`);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: SmtpConfigUpdate }) =>
      api.updateSmtpConfig(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["smtp-configs"] });
      setEditingConfig(null);
      toast.success("SMTP configuration updated successfully");
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail || error?.message || "Unknown error";
      toast.error(`Failed to update SMTP config: ${detail}`);
    },
  });

  const testMutation = useMutation({
    mutationFn: ({ id, email }: { id: string; email: string }) =>
      api.testSmtpConnection(id, email),
    onSuccess: (data) => {
      if (data.success) {
        toast.success("Connection test successful!");
      } else {
        toast.error(`Connection test failed: ${data.message}`);
      }
      setTestingId(null);
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail || error?.message || "Unknown error";
      toast.error(`Connection test failed: ${detail}`);
      setTestingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteSmtpConfig(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["smtp-configs"] });
      toast.success("SMTP configuration deleted");
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete: ${error.message}`);
    },
  });

  const handleCreateSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: SmtpConfigCreate = {
      name: formData.get("name") as string,
      host: formData.get("host") as string,
      port: parseInt(formData.get("port") as string) || 587,
      username: formData.get("username") as string,
      password: formData.get("password") as string,
      from_email: formData.get("from_email") as string,
      from_name: formData.get("from_name") as string || undefined,
      use_tls: formData.get("use_tls") === "on",
    };
    createMutation.mutate(data);
  };

  const handleUpdateSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editingConfig) return;
    const formData = new FormData(e.currentTarget);
    const password = (formData.get("password") as string)?.trim();
    const data: SmtpConfigUpdate = {
      name: formData.get("name") as string,
      host: formData.get("host") as string,
      port: parseInt(formData.get("port") as string) || 587,
      username: formData.get("username") as string,
      from_email: formData.get("from_email") as string,
      from_name: (formData.get("from_name") as string) || undefined,
      use_tls: formData.get("use_tls") === "on",
    };
    if (password) data.password = password;
    updateMutation.mutate({ id: editingConfig.id, data });
  };

  const handleTest = (id: string, email: string) => {
    setTestingId(id);
    testMutation.mutate({ id, email });
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Email Configuration</h1>
          <p className="text-muted-foreground">
            Manage SMTP settings for sending invoices
          </p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Add SMTP Config
        </Button>
      </div>

      {/* SMTP Configs Table */}
      <Card>
        <CardHeader>
          <CardTitle>SMTP Configurations</CardTitle>
          <CardDescription>
            Configure email servers for sending invoices
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading configurations...
            </div>
          ) : configs && configs.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Host</TableHead>
                  <TableHead>Port</TableHead>
                  <TableHead>From Email</TableHead>
                  <TableHead>TLS</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {configs.map((config) => (
                  <TableRow key={config.id}>
                    <TableCell className="font-medium">{config.name}</TableCell>
                    <TableCell>{config.host}</TableCell>
                    <TableCell>{config.port}</TableCell>
                    <TableCell>{config.from_email}</TableCell>
                    <TableCell>
                      {config.use_tls ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <XCircle className="h-4 w-4 text-gray-400" />
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={config.is_active ? "success" : "secondary"}>
                        {config.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleTest(config.id, config.from_email)}
                          disabled={testingId === config.id}
                          title="Test Connection"
                        >
                          <TestTube className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setEditingConfig(config)}
                          title="Edit"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => deleteMutation.mutate(config.id)}
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No SMTP configurations found. Add one to start sending emails.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add SMTP Configuration</DialogTitle>
            <DialogDescription>
              Configure a new email server for sending invoices
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateSubmit}>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Configuration Name</Label>
                <Input id="name" name="name" placeholder="e.g., Production SMTP" required />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="host">SMTP Host</Label>
                  <Input id="host" name="host" placeholder="smtp.example.com" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="port">Port</Label>
                  <Input id="port" name="port" type="number" defaultValue="587" required />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="username">Username</Label>
                  <Input id="username" name="username" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input id="password" name="password" type="password" required />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="from_email">From Email</Label>
                  <Input id="from_email" name="from_email" type="email" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="from_name">From Name</Label>
                  <Input id="from_name" name="from_name" placeholder="Billing Department" />
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="use_tls"
                  name="use_tls"
                  defaultChecked
                  className="h-4 w-4 rounded border-gray-300"
                />
                <Label htmlFor="use_tls">Use TLS/STARTTLS</Label>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Creating..." : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editingConfig} onOpenChange={() => setEditingConfig(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit SMTP Configuration</DialogTitle>
            <DialogDescription>
              Update SMTP server settings. Leave password blank to keep existing value.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleUpdateSubmit}>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="edit-name">Configuration Name</Label>
                <Input id="edit-name" name="name" defaultValue={editingConfig?.name} required />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-host">SMTP Host</Label>
                  <Input id="edit-host" name="host" defaultValue={editingConfig?.host} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-port">Port</Label>
                  <Input id="edit-port" name="port" type="number" defaultValue={editingConfig?.port ?? 587} required />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-username">Username</Label>
                  <Input id="edit-username" name="username" defaultValue={editingConfig?.username} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-password">Password (optional)</Label>
                  <Input id="edit-password" name="password" type="password" placeholder="Leave blank to keep existing" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-from_email">From Email</Label>
                  <Input id="edit-from_email" name="from_email" type="email" defaultValue={editingConfig?.from_email} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-from_name">From Name</Label>
                  <Input id="edit-from_name" name="from_name" defaultValue={editingConfig?.from_name ?? ""} />
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="edit-use_tls"
                  name="use_tls"
                  defaultChecked={!!editingConfig?.use_tls}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <Label htmlFor="edit-use_tls">Use TLS/STARTTLS</Label>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEditingConfig(null)}>
                Cancel
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Saving..." : "Save Changes"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
