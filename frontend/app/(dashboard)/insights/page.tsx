import type { Metadata } from "next";
import { AskBizz } from "@/components/ai/ask-bizz";
import { InsightCard } from "@/components/ai/insight-card";
import { PageHeader } from "@/components/layout/page-header";

export const metadata: Metadata = { title: "Insights" };

export default function InsightsPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Insights"
        description="AI-assisted explanations grounded in verified analytics — the models never invent numbers or customers."
      />
      <div className="grid grid-cols-1 items-start gap-3 xl:grid-cols-2">
        <AskBizz context={{ kind: "overview" }} />
        <InsightCard
          context={{ kind: "overview" }}
          mode="summary"
          title="Business summary"
          description="Summarize the current business picture from verified metrics and trends."
        />
      </div>
    </div>
  );
}
