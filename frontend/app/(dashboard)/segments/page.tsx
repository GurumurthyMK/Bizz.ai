import type { Metadata } from "next";
import { SegmentList } from "@/components/segments/segment-list";

export const metadata: Metadata = { title: "Segments" };

export default function SegmentsPage() {
  return <SegmentList />;
}
