"use client";

import Plot from "./PlotlyChart";
import type { StockHolding } from "@/lib/types";

export default function AllocationChart({ holdings }: { holdings: StockHolding[] }) {
  return (
    <Plot
      data={[
        {
          type: "pie",
          labels: holdings.map((h) => h.symbol),
          values: holdings.map((h) => h.weight),
          hovertemplate: "%{label}: %{percent}<extra></extra>",
          textinfo: "label+percent",
          marker: { colors: ["#667eea", "#764ba2", "#f093fb", "#4c9aff", "#20c997", "#ffc107", "#fd7e14", "#dc3545", "#28a745", "#6c757d"] },
        },
      ]}
      layout={{
        margin: { t: 20, b: 20, l: 20, r: 20 },
        showlegend: true,
        autosize: true,
        paper_bgcolor: "rgba(0,0,0,0)",
        font: { color: "currentColor" },
      }}
      useResizeHandler
      style={{ width: "100%", height: "360px" }}
      config={{ displayModeBar: false }}
    />
  );
}
