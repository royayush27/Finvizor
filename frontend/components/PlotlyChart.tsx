"use client";

import dynamic from "next/dynamic";

// Plotly touches `window` at import time, so it must never be pulled into
// the server bundle -- dynamic + ssr:false is the standard Next.js escape
// hatch for this. Every chart component below renders through this wrapper
// instead of importing react-plotly.js directly.
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

export default Plot;
