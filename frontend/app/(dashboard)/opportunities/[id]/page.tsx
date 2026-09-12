import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { OpportunityDetail } from "@/components/opportunities/opportunity-detail";

export const metadata: Metadata = { title: "Opportunity detail" };

export default function OpportunityDetailPage({ params }: { params: { id: string } }) {
  const opportunityId = Number(params.id);
  if (!Number.isInteger(opportunityId) || opportunityId <= 0) notFound();
  return <OpportunityDetail opportunityId={opportunityId} />;
}
