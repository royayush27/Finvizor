"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useWizardStore } from "@/lib/store";

export default function Sidebar() {
  const state = useWizardStore();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  return (
    <aside className="context-sidebar">
      <span className="eyebrow">YOUR WORKSPACE</span>
      <h2>Investment brief</h2>
      <dl>
        <div><dt>Capital to allocate</dt><dd>{ready ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(state.questionnaire.investment_amount) : "…"}</dd></div>
        <div><dt>Time horizon</dt><dd>{ready ? state.questionnaire.investment_timeline : "…"}</dd></div>
        <div><dt>Risk profile</dt><dd>{ready ? state.riskLevel ?? "Not assessed" : "…"}</dd></div>
        <div><dt>Sector focus</dt><dd className="brief-sectors">{ready && state.industryFocus.length ? state.industryFocus.join(", ") : "All sectors"}</dd></div>
      </dl>
      <p className="caption">Your inputs are saved in this browser.</p>
      <button className="text-button" onClick={() => { state.resetWizard(); router.push("/"); }}>Start a new brief <span aria-hidden="true">↗</span></button>
      <div className="sidebar-footnote"><span className="eyebrow">RESEARCH TOOL</span><p>Historical performance does not predict future returns. All allocations are illustrative.</p></div>
    </aside>
  );
}
