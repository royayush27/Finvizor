import type {
  EconomicSnapshot,
  IndustryInfo,
  JobStatus,
  NewsArticleSentiment,
  PortfolioRequest,
  Questionnaire,
  RiskScoreResponse,
} from "./types";

// All browser requests go through Next's server-side proxy, including local previews.
const API_BASE_URL = "";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    signal: AbortSignal.timeout(30000),
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = Array.isArray(body.detail)
      ? body.detail.map((item: { msg?: string }) => item.msg ?? "Invalid input").join(" ")
      : body.detail;
    throw new ApiError(response.status, detail ?? `Request failed (${response.status}). Please try again.`);
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
  { intervalMs = 1500, timeoutMs = 15 * 60 * 1000, signal }: { intervalMs?: number; timeoutMs?: number; signal?: AbortSignal } = {}
): Promise<JobStatus> {
  const start = Date.now();
  // eslint-disable-next-line no-constant-condition
  while (true) {
    if (signal?.aborted) throw new DOMException("Polling cancelled", "AbortError");
    const job = await api.getJobStatus(jobId);
    if (signal?.aborted) throw new DOMException("Polling cancelled", "AbortError");
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
