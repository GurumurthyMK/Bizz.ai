import type { LucideIcon } from "lucide-react";
import {
  Bell,
  Database,
  FileText,
  Layers,
  LayoutDashboard,
  Lightbulb,
  Settings,
  Target,
  TrendingUp,
  Users,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Short description shown in the command palette. */
  description: string;
}

/** Primary navigation (Design.md §5). */
export const primaryNav: NavItem[] = [
  { href: "/overview", label: "Overview", icon: LayoutDashboard, description: "Business health and what needs attention" },
  { href: "/customers", label: "Customers", icon: Users, description: "Customer intelligence profiles" },
  { href: "/segments", label: "Segments", icon: Layers, description: "Customer segment analysis" },
  { href: "/opportunities", label: "Opportunities", icon: Target, description: "Identified business opportunities" },
  { href: "/predictions", label: "Predictions", icon: TrendingUp, description: "Behavior predictions and risk signals" },
  { href: "/insights", label: "Insights", icon: Lightbulb, description: "Decision support and explanations" },
];

/** Secondary navigation (Design.md §5). */
export const secondaryNav: NavItem[] = [
  { href: "/data", label: "Data", icon: Database, description: "Data sources and dataset health" },
  { href: "/alerts", label: "Alerts", icon: Bell, description: "Business alerts" },
  { href: "/reports", label: "Reports", icon: FileText, description: "Business reports" },
  { href: "/settings", label: "Settings", icon: Settings, description: "Application settings" },
];

export const allNav: NavItem[] = [...primaryNav, ...secondaryNav];
