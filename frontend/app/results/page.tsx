"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useWizardStore } from "@/lib/store";
import type { NewsArticleSentiment } from "@/lib/types";
import InfoCard from "@/components/InfoCard";
import MetricCard from "@/components/MetricCard";
import AllocationChart from "@/components/AllocationChart";
import RiskReturnChart from "@/components/RiskReturnChart";
import SectorChart from "@/components/SectorChart";
import NewsSentimentBadge from "@/components/NewsSentimentBadge";

export default function ResultsPage() {
  const router = useRouter();
  const portfolio = useWizardStore((s) => s.portfolio);
  const setPortfolio = useWizardStore((s) => s.setPortfolio);
  const activeJob = useWizardStore((s) => s.activeJob);

  const [sentiments, setSentiments] = useState<NewsArticleSentiment[]>([]);
  const [newsUnavailable, setNewsUnavailable] = useState(false);
  const [showAiSummary, setShowAiSummary] = useState(false);
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  useEffect(() => {
    if (!portfolio) return;
    const symbols = portfolio.holdings.slice(0, 10).map((h) => h.symbol);

    Promise.all(symbols.map((s) => api.getNewsSentiment(s).catch(() => null)))
      .then((results) => {
        const valid = results.filter((r): r is NewsArticleSentiment => r !== null);
        setSentiments(valid);
        setNewsUnavailable(valid.length === 0);
      })
      .catch(() => setNewsUnavailable(true));
  }, [portfolio]);

  async function handleAiSummary() {
    if (!portfolio) return;
    setShowAiSummary(true);
    setAiLoading(true);
    setAiError(null);
    try {
      const response = await api.getAiInsights(portfolio, "ko");
      setAiSummary(response.summary);
    } catch (e) {
      setAiError(e instanceof ApiError ? e.message : "AI summary is unavailable right now.");
    } finally {
      setAiLoading(false);
    }
  }

  if (!portfolio) {
    return (
      <InfoCard>
        <p className="text-amber-600 dark:text-amber-400">
          No portfolio yet -- please complete the portfolio generation step first.
        </p>
      </InfoCard>
    );
  }

  const positiveCount = sentiments.filter((s) => s.overall_sentiment > 0.05).length;
  const negativeCount = sentiments.filter((s) => s.overall_sentiment < -0.05).length;
  const highRiskCount = sentiments.filter((s) => s.risk_level === "HIGH" || s.risk_level === "CRITICAL").length;
  const totalArticles = sentiments.reduce((sum, s) => sum + s.total_articles, 0);

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-bold">Your AI-Generated Portfolio</h1>
        <p className="text-slate-500 dark:text-slate-400">Optimized based on your preferences and market analysis.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard value={`$${portfolio.investment_amount.toLocaleString()}`} label="Total Investment" />
        <MetricCard value={String(portfolio.holdings.length)} label="Selected Stocks" />
        <MetricCard value={`${portfolio.expected_annual_return.toFixed(1)}%`} label="Expected Return" />
        <MetricCard value={String(portfolio.risk_score)} label="Risk Score" />
      </div>

      <div>
        <button
          onClick={handleAiSummary}
          className="rounded-full border border-indigo-300 px-4 py-2 text-sm font-medium text-indigo-700 transition-colors hover:bg-indigo-50 dark:border-indigo-800 dark:text-indigo-300 dark:hover:bg-indigo-950/40"
        >
          🧠 Show AI Portfolio Summary (NAVER CLOVA)
        </button>
        {showAiSummary && (
          <InfoCard className="mt-3">
            {aiLoading && <p className="text-sm text-slate-500">Generating insights...</p>}
            {aiError && <p className="text-sm text-rose-500">{aiError}</p>}
            {aiSummary && <p className="whitespace-pre-line text-sm text-slate-700 dark:text-slate-300">{aiSummary}</p>}
          </InfoCard>
        )}
      </div>

      <div>
        <h3 className="mb-3 text-lg font-semibold">News Sentiment Analysis</h3>
        {newsUnavailable ? (
          <InfoCard>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              News sentiment is unavailable -- the server may not have a NewsAPI key configured.
            </p>
          </InfoCard>
        ) : (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <MetricCard value={`${positiveCount}/${sentiments.length}`} label="Positive Sentiment" />
              <MetricCard value={`${negativeCount}/${sentiments.length}`} label="Negative Sentiment" />
              <MetricCard value={String(highRiskCount)} label="High Risk Stocks" />
              <MetricCard value={String(totalArticles)} label="News Articles" />
            </div>
            <div className="flex flex-col gap-2">
              {sentiments.map((s) => (
                <NewsSentimentBadge key={s.symbol} sentiment={s} />
              ))}
            </div>
          </div>
        )}
      </div>

      <div>
        <h3 className="mb-3 text-lg font-semibold">Portfolio Allocation</h3>
        <InfoCard>
          <AllocationChart holdings={portfolio.holdings} />
        </InfoCard>
      </div>

      <div>
        <h3 className="mb-3 text-lg font-semibold">Detailed Holdings</h3>
        <InfoCard className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
                <th className="py-2 pr-4">Symbol</th>
                <th className="py-2 pr-4">Name</th>
                <th className="py-2 pr-4">Sector</th>
                <th className="py-2 pr-4">Weight</th>
                <th className="py-2 pr-4">Price</th>
                <th className="py-2 pr-4">Exp. Return</th>
                <th className="py-2">Volatility</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.holdings.map((h) => (
                <tr key={h.symbol} className="border-b border-slate-100 dark:border-slate-900">
                  <td className="py-2 pr-4 font-semibold">{h.symbol}</td>
                  <td className="py-2 pr-4">{h.name}</td>
                  <td className="py-2 pr-4">{h.sector}</td>
                  <td className="py-2 pr-4">{(h.weight * 100).toFixed(1)}%</td>
                  <td className="py-2 pr-4">${h.current_price.toFixed(2)}</td>
                  <td className="py-2 pr-4">{h.predicted_return?.toFixed(1) ?? "—"}%</td>
                  <td className="py-2">{h.volatility.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </InfoCard>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 text-lg font-semibold">Risk-Return Analysis</h3>
          <InfoCard>
            <RiskReturnChart holdings={portfolio.holdings} />
          </InfoCard>
        </div>
        <div>
          <h3 className="mb-3 text-lg font-semibold">Sector Distribution</h3>
          <InfoCard>
            <SectorChart sectorAllocation={portfolio.sector_allocation} />
          </InfoCard>
        </div>
      </div>

      <div className="flex flex-wrap justify-center gap-3">
        {activeJob && (
          <a
            href={api.exportCsvUrl(activeJob.job_id)}
            className="rounded-full border border-slate-300 px-6 py-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-900"
          >
            💾 Download CSV
          </a>
        )}
        <button
          onClick={() => {
            setPortfolio(null);
            router.push("/portfolio-builder");
          }}
          className="rounded-full bg-brand-gradient-soft px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/30 transition-transform hover:-translate-y-0.5"
        >
          🔄 Regenerate Portfolio
        </button>
      </div>
    </div>
  );
}
