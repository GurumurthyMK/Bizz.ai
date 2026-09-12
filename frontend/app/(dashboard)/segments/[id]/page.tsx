import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { SegmentDetail } from "@/components/segments/segment-detail";

export const metadata: Metadata = { title: "Segment detail" };

export default function SegmentDetailPage({ params }: { params: { id: string } }) {
  const segmentId = Number(params.id);
  if (!Number.isInteger(segmentId) || segmentId <= 0) notFound();
  return <SegmentDetail segmentId={segmentId} />;
}
