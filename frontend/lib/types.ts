// Mirrors backend/app/models/schemas.py -- keep these in sync by hand;
// there are only a handful of shapes so a codegen step isn't worth it yet.

export type ExperienceLevel =
  | "Beginner (0-2 years)"
  | "Intermediate (2-5 years)"
  | "Advanced (5-10 years)"
  | "Expert (10+ years)";

export type RiskTolerance =
  | "Very Low Risk (Capital Preservation)"
  | "Low Risk (Stable Growth)"
  | "Medium Risk (Balanced Growth)"
  | "High Risk (Aggressive Growth)"
  | "Very High Risk (Maximum Returns)";

export type InvestmentTimeline = "< 1 Year" | "1-3 Years" | "3-5 Years" | "5-10 Years" | "> 10 Years";

export type FinancialGoal =
  | "Retirement planning"
  | "Wealth preservation"
  | "Income generation"
  | "Capital appreciation"
  | "Education funding"
  | "Emergency fund growth";

export type AnnualIncome = "< $50K" | "$50K - $100K" | "$100K - $200K" | "$200K - $500K" | "> $500K";

export type EsgPreference = "No preference" | "ESG-friendly preferred" | "Strong ESG focus only";

export type NewsRiskTolerance = "CONSERVATIVE" | "MEDIUM" | "AGGRESSIVE";

export type PortfolioMode = "ai_optimized" | "user_defined";

export type JobState = "pending" | "running" | "completed" | "failed";

export interface IndustryInfo {
  key: string;
  icon: string;
  description: string;
}

export interface Questionnaire {
  experience_level: ExperienceLevel;
  risk_tolerance: RiskTolerance;
  investment_timeline: InvestmentTimeline;
  investment_amount: number;
  financial_goal: FinancialGoal;
  annual_income: AnnualIncome;
}

export interface RiskScoreResponse {
  risk_score: number;
  risk_level: string;
  risk_color: string;
}

export interface ManualHolding {
  symbol: string;
  weight: number;
}

export interface PortfolioRequest {
  mode: PortfolioMode;
  industry_focus: string[];
  exclude_industries: string[];
  esg_preference: EsgPreference;
  questionnaire: Questionnaire;
  risk_score: number;
  news_risk_tolerance: NewsRiskTolerance;
  target_volatility?: number | null;
  target_return?: number | null;
  num_stocks: number;
  manual_holdings?: ManualHolding[] | null;
}

export interface StockHolding {
  symbol: string;
  name: string;
  sector: string;
  weight: number;
  current_price: number;
  predicted_return: number | null;
  volatility: number;
  dividend_yield: number;
  market_cap: number;
  score: number | null;
}

export interface NewsFilteringSummary {
  total_stocks_analyzed: number;
  stocks_rejected: number;
  total_articles: number;
}

export interface PortfolioResult {
  portfolio_id: string;
  generated_at: string;
  investment_amount: number;
  risk_score: number;
  expected_annual_return: number;
  portfolio_volatility: number;
  holdings: StockHolding[];
  sector_allocation: Record<string, number>;
  news_filtering_summary: NewsFilteringSummary | null;
}

export interface JobStatus {
  job_id: string;
  status: JobState;
  progress: number;
  message: string | null;
  result: PortfolioResult | null;
  error: string | null;
}

export interface NewsArticleSentiment {
  symbol: string;
  overall_sentiment: number;
  risk_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NONE";
  total_articles: number;
  summary: string;
}

export interface EconomicIndicator {
  series_id: string;
  name: string;
  value: number | null;
  previous_value: number | null;
  change_pct: number | null;
  ytd_change_pct: number | null;
  volatility_pct: number | null;
  as_of: string | null;
  source: "fred" | "yfinance_proxy" | "unavailable";
}

export interface EconomicSnapshot {
  indicators: EconomicIndicator[];
  fetched_at: string;
}
