import type { Metadata } from "next";
import { CustomerTable } from "@/components/customers/customer-table";

export const metadata: Metadata = { title: "Customers" };

export default function CustomersPage() {
  return <CustomerTable />;
}
