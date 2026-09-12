import type { Metadata } from "next";
import { DataDashboard } from "@/components/data/data-dashboard";

export const metadata: Metadata = { title: "Data" };

export default function DataPage() {
  return <DataDashboard />;
}
