"use client";

import Plot from "./PlotlyChart";
import type { StockHolding } from "@/lib/types";

export default function RiskReturnChart({ holdings }: { holdings: StockHolding[] }) {
  return (
    <Plot
      data={[
        {
          type: "scatter",
          mode: "markers+text",
          x: holdings.map((h) => h.volatility),
          y: holdings.map((h) => h.predicted_return ?? 0),
          text: holdings.map((h) => h.symbol),
          textposition: "top center",
          marker: {
            size: holdings.map((h) => Math.max(10, h.weight * 200)),
            color: holdings.map((h) => h.predicted_return ?? 0),
            colorscale: "RdYlGn",
            showscale: true,
          },
          hovertemplate: "%{text}<br>Volatility: %{x:.1f}%<br>Expected Return: %{y:.1f}%<extra></extra>",
        },
      ]}
      layout={{
        margin: { t: 20, b: 40, l: 50, r: 20 },
        xaxis: { title: "Volatility (%)" },
        yaxis: { title: "Expected Return (%)" },
        autosize: true,
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: "currentColor" },
      }}
      useResizeHandler
      style={{ width: "100%", height: "360px" }}
      config={{ displayModeBar: false }}
    />
  );
}
