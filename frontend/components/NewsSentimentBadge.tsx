import type { NewsArticleSentiment } from "@/lib/types";

const RISK_STYLES: Record<NewsArticleSentiment["risk_level"], string> = {
  CRITICAL: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  HIGH: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  MEDIUM: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  LOW: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  NONE: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
};

export default function NewsSentimentBadge({ sentiment }: { sentiment: NewsArticleSentiment }) {
  const sentimentLabel = sentiment.overall_sentiment > 0.05 ? "Positive" : sentiment.overall_sentiment < -0.05 ? "Negative" : "Neutral";

  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm dark:border-slate-800 dark:bg-slate-900">
      <span className="font-semibold text-slate-700 dark:text-slate-200">{sentiment.symbol}</span>
      <span className="text-slate-500 dark:text-slate-400">{sentimentLabel}</span>
      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${RISK_STYLES[sentiment.risk_level]}`}>
        {sentiment.risk_level}
      </span>
      <span className="text-xs text-slate-400">{sentiment.total_articles} articles</span>
    </div>
  );
}
