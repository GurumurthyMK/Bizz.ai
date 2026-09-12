import type { Metadata } from "next";
import { AlertList } from "@/components/alerts/alert-list";

export const metadata: Metadata = { title: "Alerts" };

export default function AlertsPage() {
  return <AlertList />;
}
