"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2 } from "lucide-react";
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
import type { Vendor, VendorCreate, VendorUpdate } from "@/types";

export default function VendorsPage() {
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingVendor, setEditingVendor] = useState<Vendor | null>(null);
  const [deletingVendor, setDeletingVendor] = useState<Vendor | null>(null);

  const { data: vendors, isLoading } = useQuery<Vendor[]>({
    queryKey: ["vendors"],
    queryFn: () => api.getVendors(),
  });

  const createMutation = useMutation({
    mutationFn: (data: VendorCreate) => api.createVendor(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
      setIsCreateOpen(false);
      toast.success("Vendor created successfully");
    },
    onError: (error: Error) => {
      toast.error(`Failed to create vendor: ${error.message}`);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: VendorUpdate }) =>
      api.updateVendor(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
      setEditingVendor(null);
      toast.success("Vendor updated successfully");
    },
    onError: (error: Error) => {
      toast.error(`Failed to update vendor: ${error.message}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteVendor(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
      setDeletingVendor(null);
      toast.success("Vendor deleted");
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete vendor: ${error.message}`);
    },
  });

  const handleCreateSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: VendorCreate = {
      name: formData.get("name") as string,
      email: formData.get("email") as string,
      address_line1: formData.get("address_line1") as string,
      address_line2: formData.get("address_line2") as string || undefined,
      city: formData.get("city") as string,
      province: formData.get("province") as string,
      postal_code: formData.get("postal_code") as string,
      hst_number: formData.get("hst_number") as string,
      default_contractor: formData.get("default_contractor") as string,
    };
    createMutation.mutate(data);
  };

  const handleUpdateSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editingVendor) return;
    const formData = new FormData(e.currentTarget);
    const data: VendorUpdate = {
      name: formData.get("name") as string,
      email: formData.get("email") as string,
      address_line1: formData.get("address_line1") as string,
      address_line2: (formData.get("address_line2") as string) || undefined,
      city: formData.get("city") as string,
      province: formData.get("province") as string,
      postal_code: formData.get("postal_code") as string,
      hst_number: formData.get("hst_number") as string,
      default_contractor: formData.get("default_contractor") as string,
    };
    updateMutation.mutate({ id: editingVendor.id, data });
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Vendors</h1>
          <p className="text-muted-foreground">
            Manage your company information for invoices
          </p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Add Vendor
        </Button>
      </div>

      {/* Vendors Table */}
      <Card>
        <CardHeader>
          <CardTitle>All Vendors</CardTitle>
          <CardDescription>
            Your company details that appear on invoices
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading vendors...
            </div>
          ) : vendors && vendors.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>HST Number</TableHead>
                  <TableHead>Default Contractor</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {vendors.map((vendor) => (
                  <TableRow key={vendor.id}>
                    <TableCell className="font-medium">{vendor.name}</TableCell>
                    <TableCell>{vendor.email}</TableCell>
                    <TableCell>
                      {vendor.city}, {vendor.province}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {vendor.hst_number}
                    </TableCell>
                    <TableCell>{vendor.default_contractor}</TableCell>
                    <TableCell>
                      <Badge variant={vendor.is_active ? "success" : "secondary"}>
                        {vendor.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setEditingVendor(vendor)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setDeletingVendor(vendor)}
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
              No vendors found. Create your first vendor to get started.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add New Vendor</DialogTitle>
            <DialogDescription>
              Add your company information for invoices
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateSubmit}>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Company Name</Label>
                  <Input id="name" name="name" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" name="email" type="email" required />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="address_line1">Address Line 1</Label>
                <Input id="address_line1" name="address_line1" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="address_line2">Address Line 2</Label>
                <Input id="address_line2" name="address_line2" />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="city">City</Label>
                  <Input id="city" name="city" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="province">Province</Label>
                  <Input id="province" name="province" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="postal_code">Postal Code</Label>
                  <Input id="postal_code" name="postal_code" required />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="hst_number">HST Number</Label>
                  <Input id="hst_number" name="hst_number" placeholder="123456789RT0001" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="default_contractor">Default Contractor Name</Label>
                  <Input id="default_contractor" name="default_contractor" required />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Creating..." : "Create Vendor"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editingVendor} onOpenChange={() => setEditingVendor(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Vendor</DialogTitle>
            <DialogDescription>
              Update vendor information
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleUpdateSubmit}>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-name">Company Name</Label>
                  <Input id="edit-name" name="name" defaultValue={editingVendor?.name} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-email">Email</Label>
                  <Input id="edit-email" name="email" type="email" defaultValue={editingVendor?.email} required />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-address_line1">Address Line 1</Label>
                <Input id="edit-address_line1" name="address_line1" defaultValue={editingVendor?.address_line1} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-address_line2">Address Line 2</Label>
                <Input id="edit-address_line2" name="address_line2" defaultValue={editingVendor?.address_line2 ?? ""} />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-city">City</Label>
                  <Input id="edit-city" name="city" defaultValue={editingVendor?.city} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-province">Province</Label>
                  <Input id="edit-province" name="province" defaultValue={editingVendor?.province} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-postal_code">Postal Code</Label>
                  <Input id="edit-postal_code" name="postal_code" defaultValue={editingVendor?.postal_code} required />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-hst_number">HST Number</Label>
                  <Input id="edit-hst_number" name="hst_number" defaultValue={editingVendor?.hst_number} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-default_contractor">Default Contractor</Label>
                  <Input id="edit-default_contractor" name="default_contractor" defaultValue={editingVendor?.default_contractor} required />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEditingVendor(null)}>
                Cancel
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Saving..." : "Save Changes"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deletingVendor} onOpenChange={() => setDeletingVendor(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Vendor</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete {deletingVendor?.name}? This will also
              remove all associated customers and invoices.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingVendor(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deletingVendor && deleteMutation.mutate(deletingVendor.id)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
