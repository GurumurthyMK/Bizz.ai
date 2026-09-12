"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, Target } from "lucide-react";
import { AskBizz } from "@/components/ai/ask-bizz";
import { InsightCard } from "@/components/ai/insight-card";
import { PageHeader } from "@/components/layout/page-header";
import { AttentionCard } from "@/components/overview/attention-card";
import { KpiCard } from "@/components/overview/kpi-card";
import { OpportunityCard } from "@/components/overview/opportunity-card";
import { ActivityChart, RevenueTrendChart } from "@/components/overview/trend-charts";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useOverview } from "@/hooks/use-overview";
import { formatCurrency, formatNumber } from "@/lib/format";

const investigateLinks = [
  { label: "Customers", href: "/customers" },
  { label: "Segments", href: "/segments" },
  { label: "Predictions", href: "/predictions" },
  { label: "Opportunities", href: "/opportunities" },
  { label: "Insights", href: "/insights" },
];

function SectionHeading({ id, title, hint }: { id: string; title: string; hint?: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <h2 id={id} className="text-section-title">
        {title}
      </h2>
      {hint != null && <p className="text-sm text-muted-foreground">{hint}</p>}
    </div>
  );
}

function OverviewSkeleton() {
  return (
    <div className="flex flex-col gap-6" role="status" aria-label="Loading business overview">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {["revenue", "customers", "orders", "aov"].map((key) => (
          <Skeleton key={key} className="h-28" />
        ))}
      </div>
      <Skeleton className="h-48" />
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
      </div>
      <span className="sr-only">Loading business overview…</span>
    </div>
  );
}

/**
 * Primary business intelligence screen: health, attention, opportunities,
 * trends, and investigation paths — every number from GET /api/v1/overview.
 */
export function OverviewDashboard() {
  const { data, loading, error, retry } = useOverview();

  if (loading) {
    return (
      <div className="flex flex-col gap-5">
        <PageHeader
          title="Overview"
          description="Business health, important changes, and items that need attention."
        />
        <OverviewSkeleton />
      </div>
    );
  }

  if (error !== null || data === null) {
    return (
      <div className="flex flex-col gap-5">
        <PageHeader
          title="Overview"
          description="Business health, important changes, and items that need attention."
        />
        <ErrorState
          title="Unable to load the overview"
          description={error ?? "The analytics service could not be reached."}
          onRetry={retry}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Overview"
        description={`Trailing 30 days vs the prior period · ${formatNumber(data.meta.customer_count)} customers on record.`}
      />

      <section aria-labelledby="business-health">
        <div className="flex flex-col gap-3">
          <SectionHeading
            id="business-health"
            title="Business health"
            hint="What is happening right now."
          />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard kpi={data.health.revenue} formatValue={formatCurrency} />
            <KpiCard kpi={data.health.active_customers} formatValue={formatNumber} />
            <KpiCard kpi={data.health.transactions} formatValue={formatNumber} />
            <KpiCard
              kpi={data.health.avg_order_value}
              formatValue={formatCurrency}
              context="per completed order"
            />
          </div>
        </div>
      </section>

      <section aria-labelledby="needs-attention">
        <div className="flex flex-col gap-3">
          <SectionHeading
            id="needs-attention"
            title="What needs attention"
            hint="Why it matters, and where to investigate."
          />
          {data.attention.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="Nothing needs attention"
              description="No deteriorating signals in the current window. KPIs above still show the full picture."
            />
          ) : (
            <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
              {data.attention.map((item) => (
                <AttentionCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section aria-labelledby="opportunities">
        <div className="flex flex-col gap-3">
          <SectionHeading
            id="opportunities"
            title="Opportunities"
            hint="Where value may exist next, with supporting evidence."
          />
          {!data.meta.ml_available ? (
            <EmptyState
              icon={Target}
              title="Opportunity scoring unavailable"
              description="The prediction models have not been trained yet, so there is nothing to rank. Health, trends, and attention above are unaffected."
            />
          ) : data.opportunities.length === 0 ? (
            <EmptyState
              icon={Target}
              title="No opportunities standing out"
              description="No customers currently score above the opportunity threshold."
            />
          ) : (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {data.opportunities.map((item) => (
                <OpportunityCard key={item.customer_id} item={item} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section aria-labelledby="business-trends">
        <div className="flex flex-col gap-3">
          <SectionHeading
            id="business-trends"
            title="Business trends"
            hint="Six 30-day periods ending at the reference date."
          />
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
            <RevenueTrendChart trends={data.trends} />
            <ActivityChart trends={data.trends} />
          </div>
        </div>
      </section>

      <section aria-labelledby="ai-explanations">
        <div className="flex flex-col gap-3">
          <SectionHeading
            id="ai-explanations"
            title="AI-assisted explanations"
            hint="Generated from the verified metrics above — never a source of numbers."
          />
          <div className="grid grid-cols-1 items-start gap-3 xl:grid-cols-2">
            <InsightCard
              context={{ kind: "overview" }}
              title="Bizz Insight"
              description="Explain what changed in this dashboard, why it matters, and what to investigate."
            />
            <AskBizz context={{ kind: "overview" }} />
          </div>
        </div>
      </section>

      <section aria-labelledby="investigate">
        <div className="flex flex-col gap-3">
          <SectionHeading
            id="investigate"
            title="Investigate further"
            hint="Move from a signal above into the workflow behind it."
          />
          <nav aria-label="Investigation workflows" className="flex flex-wrap gap-2">
            {investigateLinks.map((link) => (
              <Button key={link.href} variant="outline" size="sm" asChild>
                <Link href={link.href}>
                  {link.label}
                  <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            ))}
          </nav>
        </div>
      </section>
    </div>
  );
}
