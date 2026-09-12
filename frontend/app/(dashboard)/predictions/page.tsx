import type { Metadata } from "next";
import { PredictionTable } from "@/components/predictions/prediction-table";

export const metadata: Metadata = { title: "Predictions" };

function toCustomerId(value: string | string[] | undefined): number | undefined {
  const text = Array.isArray(value) ? value[0] : value;
  if (text === undefined || text.trim() === "" || !Number.isInteger(Number(text))) {
    return undefined;
  }
  return Number(text);
}

function toType(value: string | string[] | undefined): "churn" | "purchase" | undefined {
  const text = Array.isArray(value) ? value[0] : value;
  return text === "churn" || text === "purchase" ? text : undefined;
}

export default function PredictionsPage({
  searchParams,
}: {
  searchParams: { customer_id?: string | string[]; prediction_type?: string | string[] };
}) {
  return (
    <PredictionTable
      initialCustomerId={toCustomerId(searchParams.customer_id)}
      initialType={toType(searchParams.prediction_type)}
    />
  );
}
