import type { NewsArticleSentiment } from "@/lib/types";

const RISK_STYLES: Record<NewsArticleSentiment["risk_level"], string> = {
  UNKNOWN: "bg-slate-100 text-slate-600",
  CRITICAL: "bg-red-100 text-red-800  ",
  HIGH: "bg-red-100 text-red-800  ",
  MEDIUM: "bg-amber-100 text-amber-800  ",
  LOW: "bg-emerald-100 text-emerald-800  ",
  NONE: "bg-emerald-100 text-emerald-800  ",
};

export default function NewsSentimentBadge({ sentiment }: { sentiment: NewsArticleSentiment }) {
  const sentimentLabel = sentiment.overall_sentiment > 0.05 ? "Positive" : sentiment.overall_sentiment < -0.05 ? "Negative" : "Neutral";

  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-slate-200 bg-white px-4 py-2 text-sm  ">
      <span className="font-semibold text-slate-700 ">{sentiment.symbol}</span>
      <span className="text-slate-500 ">{sentiment.risk_level === "UNKNOWN" ? "No coverage" : sentimentLabel}</span>
      <span className={`rounded px-2 py-0.5 text-xs font-medium ${RISK_STYLES[sentiment.risk_level]}`}>
        {sentiment.risk_level}
      </span>
      <span className="text-xs text-slate-400">{sentiment.total_articles} articles</span>
    </div>
  );
}
