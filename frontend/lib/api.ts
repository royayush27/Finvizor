import type {
  EconomicSnapshot,
  IndustryInfo,
  JobStatus,
  NewsArticleSentiment,
  PortfolioRequest,
  Questionnaire,
  RiskScoreResponse,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body.detail ?? `Request to ${path} failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  getIndustries: () => request<IndustryInfo[]>("/api/industries"),

  scoreRisk: (questionnaire: Questionnaire) =>
    request<RiskScoreResponse>("/api/risk/score", {
      method: "POST",
      body: JSON.stringify({ questionnaire }),
    }),

  generatePortfolio: (payload: PortfolioRequest) =>
    request<JobStatus>("/api/portfolio/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getJobStatus: (jobId: string) => request<JobStatus>(`/api/portfolio/jobs/${jobId}`),

  exportCsvUrl: (jobId: string) => `${API_BASE_URL}/api/portfolio/jobs/${jobId}/export.csv`,

  getNewsSentiment: (symbol: string) => request<NewsArticleSentiment>(`/api/news/${symbol}`),

  getEconomicData: () => request<EconomicSnapshot>("/api/economic-data"),

  getAiInsights: (portfolio: unknown, language: "ko" | "en" = "ko") =>
    request<{ summary: string }>("/api/insights", {
      method: "POST",
      body: JSON.stringify({ portfolio, language }),
    }),
};

export { ApiError };

/** Poll a portfolio-generation job until it completes or fails. */
export async function pollJobUntilDone(
  jobId: string,
  onProgress: (job: JobStatus) => void,
  { intervalMs = 1500, timeoutMs = 5 * 60 * 1000 }: { intervalMs?: number; timeoutMs?: number } = {}
): Promise<JobStatus> {
  const start = Date.now();
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const job = await api.getJobStatus(jobId);
    onProgress(job);
    if (job.status === "completed" || job.status === "failed") {
      return job;
    }
    if (Date.now() - start > timeoutMs) {
      throw new Error("Timed out waiting for portfolio generation.");
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}
