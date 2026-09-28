"use client";

import Plot from "./PlotlyChart";

export default function SectorChart({ sectorAllocation }: { sectorAllocation: Record<string, number> }) {
  const sectors = Object.keys(sectorAllocation);
  const weights = Object.values(sectorAllocation).map((w) => w * 100);

  return (
    <Plot
      data={[
        {
          type: "bar",
          x: sectors,
          y: weights,
          marker: { color: "#667eea" },
          hovertemplate: "%{x}: %{y:.1f}%<extra></extra>",
        },
      ]}
      layout={{
        margin: { t: 20, b: 80, l: 50, r: 20 },
        yaxis: { title: "Allocation (%)" },
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
