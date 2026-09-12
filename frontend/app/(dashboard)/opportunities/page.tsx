import type { Metadata } from "next";
import { OpportunityTable } from "@/components/opportunities/opportunity-table";

export const metadata: Metadata = { title: "Opportunities" };

function toId(value: string | string[] | undefined): number | undefined {
  const text = Array.isArray(value) ? value[0] : value;
  if (text === undefined || text.trim() === "" || !Number.isInteger(Number(text))) {
    return undefined;
  }
  return Number(text);
}

export default function OpportunitiesPage({
  searchParams,
}: {
  searchParams: { customer_id?: string | string[]; segment_id?: string | string[] };
}) {
  return (
    <OpportunityTable
      initialCustomerId={toId(searchParams.customer_id)}
      initialSegmentId={toId(searchParams.segment_id)}
    />
  );
}
