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
          marker: { colors: ["#245744", "#6b8768", "#aab89a", "#b89e6c", "#637e80", "#c1bca8", "#897966", "#91a5a0", "#b9c8bb", "#657365"] },
        },
      ]}
      layout={{
        margin: { t: 20, b: 20, l: 20, r: 20 },
        showlegend: true,
        autosize: true,
        paper_bgcolor: "rgba(0,0,0,0)",
        font: { color: "#3d4a40" },
      }}
      useResizeHandler
      style={{ width: "100%", height: "360px" }}
      config={{ displayModeBar: false }}
    />
  );
}
