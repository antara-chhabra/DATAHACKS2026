"use client";
import { useState } from "react";
import dynamic from "next/dynamic";
import { useTheme } from "@/app/ThemeContext";
import cardStyles from "./Card.module.css";
import styles from "./Volatility3D.module.css";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false }) as any;

function generateVolSurface(baseVol: number, periods: number, strikes: number) {
  const z: number[][] = [];
  for (let i = 0; i < periods; i++) {
    const row: number[] = [];
    for (let j = 0; j < strikes; j++) {
      const t = i / (periods - 1);
      const k = (j / (strikes - 1)) * 2 - 1;
      const smile = baseVol * (1 + 0.4 * k * k);
      const timeDecay = 1 + 0.6 * (1 - t);
      const noise = (Math.sin(i * 0.7 + j * 0.5) + Math.cos(i * 0.3)) * baseVol * 0.15;
      row.push(+(smile * timeDecay + noise).toFixed(4));
    }
    z.push(row);
  }
  return z;
}

const PERIODS = 20;
const STRIKES = 20;

const X = Array.from({ length: STRIKES }, (_, i) => +((0.3 + i * 0.025).toFixed(3)));
const Y = Array.from({ length: PERIODS }, (_, i) => i * 4);

const ASSETS = [
  { id: "btc", label: "BTC", baseVol: 0.031, color: "#f59e0b", colorscale: "YlOrBr" },
  { id: "eth", label: "ETH", baseVol: 0.048, color: "#6366f1", colorscale: "Purples" },
  { id: "sol", label: "SOL", baseVol: 0.071, color: "#8b5cf6", colorscale: "Magma" },
];

export default function Volatility3D() {
  const { theme } = useTheme();
  const dark = theme === "dark";
  const [selected, setSelected] = useState<string>("btc");

  const asset = ASSETS.find((a) => a.id === selected) ?? ASSETS[0];
  const Z = generateVolSurface(asset.baseVol, PERIODS, STRIKES);

  const paperBg = dark ? "#180f30" : "#ffffff";
  const plotBg = dark ? "#1a1335" : "#faf9ff";
  const gridColor = dark ? "#2d1f55" : "#e5e0f5";
  const fontColor = dark ? "#c4b5fd" : "#4c1d95";

  return (
    <div className={cardStyles.card}>
      <div className={cardStyles.cardTitle}>3D Volatility Surface</div>
      <p className={styles.intro}>
        Implied volatility surface across strike price × time horizon for each prediction market coin.
        Higher surfaces indicate greater uncertainty and wider spreads in the order book.
      </p>

      <div className={styles.tabs}>
        {ASSETS.map((a) => (
          <button
            key={a.id}
            className={`${styles.tab} ${selected === a.id ? styles.tabActive : ""}`}
            style={selected === a.id ? { borderColor: a.color, color: a.color, background: a.color + "18" } : {}}
            onClick={() => setSelected(a.id)}
          >
            {a.label}
            <span className={styles.tabVol}>σ={a.baseVol}</span>
          </button>
        ))}
      </div>

      <div className={styles.chartWrap}>
        <Plot
          data={[
            {
              type: "surface",
              x: X,
              y: Y,
              z: Z,
              colorscale: asset.colorscale,
              opacity: 0.9,
              showscale: false,
              contours: {
                z: { show: true, usecolormap: true, highlightcolor: asset.color, project: { z: true } },
              },
            } as any,
          ]}
          layout={{
            autosize: true,
            height: 340,
            margin: { l: 0, r: 0, t: 0, b: 0 },
            paper_bgcolor: paperBg,
            plot_bgcolor: plotBg,
            scene: {
              bgcolor: plotBg,
              xaxis: {
                title: { text: "Strike", font: { color: fontColor, size: 10 } },
                gridcolor: gridColor,
                zerolinecolor: gridColor,
                tickfont: { color: fontColor, size: 9 },
              },
              yaxis: {
                title: { text: "Time (ticks)", font: { color: fontColor, size: 10 } },
                gridcolor: gridColor,
                zerolinecolor: gridColor,
                tickfont: { color: fontColor, size: 9 },
              },
              zaxis: {
                title: { text: "Implied Vol", font: { color: fontColor, size: 10 } },
                gridcolor: gridColor,
                zerolinecolor: gridColor,
                tickfont: { color: fontColor, size: 9 },
              },
              camera: { eye: { x: 1.4, y: -1.4, z: 0.9 } },
            },
            font: { family: "Roboto Mono", color: fontColor },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%" }}
        />
      </div>

      <div className={styles.legend}>
        <div className={styles.legendItem}>
          <span className={styles.legendDot} style={{ background: asset.color }} />
          <span>Higher surface = more uncertain market pricing</span>
        </div>
        <div className={styles.legendItem}>
          <span className={styles.legendDot} style={{ background: "#10b981" }} />
          <span>Lower vol regions = higher strategy confidence</span>
        </div>
      </div>
    </div>
  );
}
