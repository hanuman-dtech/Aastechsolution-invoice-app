"use client";

import { FormEvent, useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, Eye, MoreHorizontal } from "lucide-react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import { formatCurrency, getFrequencyLabel } from "@/lib/utils";
import type { Customer, CustomerCreate, CustomerUpdate, Vendor, CANADIAN_PROVINCES } from "@/types";

export default function CustomersPage() {
  const queryClient = useQueryClient();
  const paymentTermOptions = [
    "Due on Receipt",
    "Net 7",
    "Net 10",
    "Net 15",
    "Net 30",
    "Net 45",
    "Net 60",
    "Monthly",
  ];
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [deletingCustomer, setDeletingCustomer] = useState<Customer | null>(null);
  const [contractorRegistry, setContractorRegistry] = useState<string[]>([]);
  const [newContractorName, setNewContractorName] = useState("");
  const [createPaymentTerms, setCreatePaymentTerms] = useState("Monthly");
  const [editPaymentTerms, setEditPaymentTerms] = useState("Monthly");

  const { data: customers, isLoading } = useQuery<Customer[]>({
    queryKey: ["customers"],
    queryFn: () => api.getCustomers(),
  });

  const { data: vendors } = useQuery<Vendor[]>({
    queryKey: ["vendors"],
    queryFn: () => api.getVendors(),
  });

  const contractorOptions = Array.from(
    new Set([
      ...(customers ?? []).map((c) => c.contractor_name?.trim()).filter(Boolean),
      ...(vendors ?? []).map((v) => v.default_contractor?.trim()).filter(Boolean),
      ...contractorRegistry,
    ])
  ) as string[];

  useEffect(() => {
    const raw = localStorage.getItem("invoice-enterprise-contractor-registry");
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as string[];
      if (Array.isArray(parsed)) {
        setContractorRegistry(parsed.filter(Boolean));
      }
    } catch {
      // Ignore malformed local storage values.
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(
      "invoice-enterprise-contractor-registry",
      JSON.stringify(contractorRegistry)
    );
  }, [contractorRegistry]);

  useEffect(() => {
    setEditPaymentTerms(editingCustomer?.contract?.payment_terms ?? "Monthly");
  }, [editingCustomer]);

  const handleRegisterContractor = () => {
    const name = newContractorName.trim();
    if (!name) {
      toast.error("Enter a contractor name to register");
      return;
    }
    if (contractorOptions.some((n) => n.toLowerCase() === name.toLowerCase())) {
      toast.error("Contractor already exists");
      return;
    }
    setContractorRegistry((prev) => [...prev, name]);
    setNewContractorName("");
    toast.success("Contractor registered");
  };

  const createMutation = useMutation({
    mutationFn: (data: CustomerCreate) => api.createCustomer(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      setIsCreateOpen(false);
      setCreatePaymentTerms("Monthly");
      toast.success("Customer created successfully");
    },
    onError: (error: Error) => {
      toast.error(`Failed to create customer: ${error.message}`);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: CustomerUpdate }) =>
      api.updateCustomer(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      setEditingCustomer(null);
      toast.success("Customer updated successfully");
    },
    onError: (error: Error) => {
      toast.error(`Failed to update customer: ${error.message}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteCustomer(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      setDeletingCustomer(null);
      toast.success("Customer deleted successfully");
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete customer: ${error.message}`);
    },
  });

  const handleCreateSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data: CustomerCreate = {
      vendor_id: formData.get("vendor_id") as string,
      name: formData.get("name") as string,
      email: formData.get("email") as string,
      address_line1: formData.get("address_line1") as string,
      address_line2: formData.get("address_line2") as string || undefined,
      city: formData.get("city") as string,
      province: formData.get("province") as string,
      postal_code: formData.get("postal_code") as string,
      contractor_name: formData.get("contractor_name") as string,
      service_location: formData.get("service_location") as string || undefined,
      payment_terms: (formData.get("payment_terms") as string) || undefined,
    };
    createMutation.mutate(data);
  };

  const handleUpdateSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editingCustomer) return;
    const formData = new FormData(e.currentTarget);
    const data: CustomerUpdate = {
      name: formData.get("name") as string,
      email: formData.get("email") as string,
      address_line1: formData.get("address_line1") as string,
      address_line2: formData.get("address_line2") as string || undefined,
      city: formData.get("city") as string,
      province: formData.get("province") as string,
      postal_code: formData.get("postal_code") as string,
      contractor_name: formData.get("contractor_name") as string,
      service_location: formData.get("service_location") as string || undefined,
      payment_terms: (formData.get("payment_terms") as string) || undefined,
    };
    updateMutation.mutate({ id: editingCustomer.id, data });
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Customers</h1>
          <p className="text-muted-foreground">
            Manage your customers and their billing contracts
          </p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Add Customer
        </Button>
      </div>

      {/* Customers Table */}
      <Card>
        <CardHeader>
          <CardTitle>Contractor Names</CardTitle>
          <CardDescription>
            Register contractor names once, then choose them in customer forms
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Add contractor name"
              value={newContractorName}
              onChange={(e) => setNewContractorName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleRegisterContractor();
                }
              }}
            />
            <Button type="button" onClick={handleRegisterContractor}>
              Register
            </Button>
          </div>

          {contractorOptions.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {contractorOptions.map((name) => (
                <Badge key={name} variant="outline">
                  {name}
                </Badge>
              ))}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              No contractor names registered yet.
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>All Customers</CardTitle>
          <CardDescription>
            {customers?.length ?? 0} total customers
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading customers...
            </div>
          ) : customers && customers.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Frequency</TableHead>
                  <TableHead>Rate</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {customers.map((customer) => (
                  <TableRow key={customer.id}>
                    <TableCell className="font-medium">
                      {customer.name}
                    </TableCell>
                    <TableCell>{customer.email}</TableCell>
                    <TableCell>
                      {customer.city}, {customer.province}
                    </TableCell>
                    <TableCell>
                      {customer.contract
                        ? getFrequencyLabel(customer.contract.frequency)
                        : "-"}
                    </TableCell>
                    <TableCell>
                      {customer.contract
                        ? formatCurrency(customer.contract.rate_per_hour)
                        : "-"}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={customer.is_active ? "success" : "secondary"}
                      >
                        {customer.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setEditingCustomer(customer)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setDeletingCustomer(customer)}
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
              No customers found. Create your first customer to get started.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add New Customer</DialogTitle>
            <DialogDescription>
              Create a new customer for invoice generation
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateSubmit}>
            <input type="hidden" name="payment_terms" value={createPaymentTerms} />
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="vendor_id">Vendor</Label>
                  <Select name="vendor_id" required>
                    <SelectTrigger>
                      <SelectValue placeholder="Select vendor" />
                    </SelectTrigger>
                    <SelectContent>
                      {vendors?.map((vendor) => (
                        <SelectItem key={vendor.id} value={vendor.id}>
                          {vendor.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="name">Customer Name</Label>
                  <Input id="name" name="name" required />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" name="email" type="email" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="contractor_name">Contractor Name</Label>
                  <Input
                    id="contractor_name"
                    name="contractor_name"
                    list="contractor-options"
                    placeholder="Select or type contractor"
                    required
                  />
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
              <div className="space-y-2">
                <Label htmlFor="service_location">Service Location</Label>
                <Input
                  id="service_location"
                  name="service_location"
                  placeholder="e.g., Ontario, Canada"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="payment_terms">Payment Terms</Label>
                <Select value={createPaymentTerms} onValueChange={setCreatePaymentTerms}>
                  <SelectTrigger id="payment_terms">
                    <SelectValue placeholder="Select payment terms" />
                  </SelectTrigger>
                  <SelectContent>
                    {paymentTermOptions.map((term) => (
                      <SelectItem key={term} value={term}>
                        {term}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsCreateOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Creating..." : "Create Customer"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog
        open={!!editingCustomer}
        onOpenChange={() => setEditingCustomer(null)}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Customer</DialogTitle>
            <DialogDescription>
              Update customer information
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleUpdateSubmit}>
            <input type="hidden" name="payment_terms" value={editPaymentTerms} />
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-name">Customer Name</Label>
                  <Input
                    id="edit-name"
                    name="name"
                    defaultValue={editingCustomer?.name}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-email">Email</Label>
                  <Input
                    id="edit-email"
                    name="email"
                    type="email"
                    defaultValue={editingCustomer?.email}
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-contractor_name">Contractor Name</Label>
                <Input
                  id="edit-contractor_name"
                  name="contractor_name"
                  list="contractor-options"
                  placeholder="Select or type contractor"
                  defaultValue={editingCustomer?.contractor_name}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-address_line1">Address Line 1</Label>
                <Input
                  id="edit-address_line1"
                  name="address_line1"
                  defaultValue={editingCustomer?.address_line1}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-address_line2">Address Line 2</Label>
                <Input
                  id="edit-address_line2"
                  name="address_line2"
                  defaultValue={editingCustomer?.address_line2 ?? ""}
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-city">City</Label>
                  <Input
                    id="edit-city"
                    name="city"
                    defaultValue={editingCustomer?.city}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-province">Province</Label>
                  <Input
                    id="edit-province"
                    name="province"
                    defaultValue={editingCustomer?.province}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-postal_code">Postal Code</Label>
                  <Input
                    id="edit-postal_code"
                    name="postal_code"
                    defaultValue={editingCustomer?.postal_code}
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-service_location">Service Location</Label>
                <Input
                  id="edit-service_location"
                  name="service_location"
                  defaultValue={editingCustomer?.service_location}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-payment_terms">Payment Terms</Label>
                <Select value={editPaymentTerms} onValueChange={setEditPaymentTerms}>
                  <SelectTrigger id="edit-payment_terms">
                    <SelectValue placeholder="Select payment terms" />
                  </SelectTrigger>
                  <SelectContent>
                    {paymentTermOptions.map((term) => (
                      <SelectItem key={term} value={term}>
                        {term}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditingCustomer(null)}
              >
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
      <Dialog
        open={!!deletingCustomer}
        onOpenChange={() => setDeletingCustomer(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Customer</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete {deletingCustomer?.name}? This
              action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeletingCustomer(null)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() =>
                deletingCustomer && deleteMutation.mutate(deletingCustomer.id)
              }
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <datalist id="contractor-options">
        {contractorOptions.map((name) => (
          <option key={name} value={name} />
        ))}
      </datalist>
    </div>
  );
}
