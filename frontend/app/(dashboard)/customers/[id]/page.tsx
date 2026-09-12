import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CustomerDetail } from "@/components/customers/customer-detail";

export const metadata: Metadata = { title: "Customer detail" };

export default function CustomerDetailPage({ params }: { params: { id: string } }) {
  const customerId = Number(params.id);
  if (!Number.isInteger(customerId) || customerId <= 0) notFound();
  return <CustomerDetail customerId={customerId} />;
}
