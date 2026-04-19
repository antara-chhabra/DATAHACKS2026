"use client";
import { useState, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend,
} from "recharts";
import styles from "./Charts.module.css";
import cardStyles from "./Card.module.css";

type TSPoint = { tick: number; ts: number; value: number };
type TSData = Record<string, TSPoint[]>;

const HOURS = ["20h", "40h", "80h", "160h"] as const;
type HourKey = typeof HOURS[number];

const LINE_CONFIGS = [
  { key: "BTC_5m",     label: "BTC 5m",     color: "#f59e0b", asset: "BTC", interval: "5m" },
  { key: "ETH_5m",     label: "ETH 5m",     color: "#6366f1", asset: "ETH", interval: "5m" },
  { key: "SOL_5m",     label: "SOL 5m",     color: "#8b5cf6", asset: "SOL", interval: "5m" },
  { key: "BTC_15m",    label: "BTC 15m",    color: "#f97316", asset: "BTC", interval: "15m" },
  { key: "ETH_15m",    label: "ETH 15m",    color: "#3b82f6", asset: "ETH", interval: "15m" },
  { key: "SOL_15m",    label: "SOL 15m",    color: "#a78bfa", asset: "SOL", interval: "15m" },
  { key: "BTC_hourly", label: "BTC 1h",     color: "#d97706", asset: "BTC", interval: "1h" },
  { key: "ETH_hourly", label: "ETH 1h",     color: "#4338ca", asset: "ETH", interval: "1h" },
  { key: "SOL_hourly", label: "SOL 1h",     color: "#7c3aed", asset: "SOL", interval: "1h" },
];

const ASSET_AGGS = [
  { key: "btc_agg", label: "BTC (all)", color: "#f59e0b", keys: ["BTC_5m","BTC_15m","BTC_hourly"] },
  { key: "eth_agg", label: "ETH (all)", color: "#6366f1", keys: ["ETH_5m","ETH_15m","ETH_hourly"] },
  { key: "sol_agg", label: "SOL (all)", color: "#8b5cf6", keys: ["SOL_5m","SOL_15m","SOL_hourly"] },
];

function normalize(points: TSPoint[]) {
  if (!points || points.length === 0) return [];
  const base = points[0].value;
  return points.map((p, i) => ({
    x: i,
    pct: +((p.value / base - 1) * 100).toFixed(2),
    val: p.value,
    ts: p.ts,
  }));
}

function avgAgg(datasets: TSPoint[][], length: number) {
  const result = [];
  for (let i = 0; i < length; i++) {
    const vals = datasets.map((d) => {
      const idx = Math.min(i, d.length - 1);
      return d[idx]?.value ?? 10000;
    });
    const avg = vals.reduce((s, v) => s + v, 0) / vals.length;
    result.push({ value: avg, ts: 0, tick: i });
  }
  return result;
}

function fmtDollar(v: number) {
  return "$" + v.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function CustomTooltip1({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{ background: "#fff", border: "1px solid #e5e0f5", borderRadius: 8, padding: "8px 12px", fontSize: 12 }}>
      <div style={{ fontFamily: "Roboto Mono", color: "#4c1d95", marginBottom: 4 }}>
        {fmtDollar(d.val)}
      </div>
      <div style={{ color: "#6b7280" }}>
        {d.pct >= 0 ? "+" : ""}{d.pct}% return
      </div>
    </div>
  );
}

function CustomTooltip2({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#fff", border: "1px solid #e5e0f5", borderRadius: 8, padding: "8px 12px", fontSize: 12 }}>
      {payload.map((p: any) => (
        <div key={p.name} style={{ color: p.color, fontFamily: "Roboto Mono", marginBottom: 2 }}>
          {p.name}: {p.value >= 0 ? "+" : ""}{p.value}%
        </div>
      ))}
    </div>
  );
}

export default function Charts() {
  const [tsData, setTsData] = useState<TSData | null>(null);
  const [selectedHours, setSelectedHours] = useState<HourKey>("80h");
  const [showIndividual, setShowIndividual] = useState(false);
  const [visibleLines, setVisibleLines] = useState<Set<string>>(
    new Set(ASSET_AGGS.map((a) => a.key))
  );

  useEffect(() => {
    fetch("/timeseries.json")
      .then((r) => r.json())
      .then(setTsData)
      .catch(console.error);
  }, []);

  if (!tsData) {
    return (
      <div className={cardStyles.card} style={{ minHeight: 400, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ color: "var(--text-muted)", fontFamily: "Roboto Mono", fontSize: 13 }}>Loading chart data...</span>
      </div>
    );
  }

  // Chart 1: Strategy Growth
  const growthKey = selectedHours === "20h" ? "20h" : selectedHours === "40h" ? "40h" : selectedHours === "80h" ? "80h" : "160h";
  const growthData = normalize(tsData[growthKey] ?? []);

  // Chart 2: Performance Across Markets
  const lineLength = 80;
  const aggData: Record<string, TSPoint[]> = {};
  ASSET_AGGS.forEach((ag) => {
    const datasets = ag.keys.map((k) => tsData[k] ?? []).filter((d) => d.length > 0);
    if (datasets.length > 0) aggData[ag.key] = avgAgg(datasets, lineLength);
  });

  const perf2 = Array.from({ length: lineLength }, (_, i) => {
    const row: Record<string, number> = { x: i };
    if (showIndividual) {
      LINE_CONFIGS.forEach((lc) => {
        if (visibleLines.has(lc.key)) {
          const d = tsData[lc.key];
          if (d && d.length > 0) {
            const base = d[0].value;
            const val = d[Math.min(i, d.length - 1)].value;
            row[lc.key] = +((val / base - 1) * 100).toFixed(2);
          }
        }
      });
    } else {
      ASSET_AGGS.forEach((ag) => {
        if (visibleLines.has(ag.key)) {
          const d = aggData[ag.key];
          if (d && d.length > 0) {
            const base = d[0].value;
            const val = d[Math.min(i, d.length - 1)].value;
            row[ag.key] = +((val / base - 1) * 100).toFixed(2);
          }
        }
      });
    }
    return row;
  });

  function toggleLine(key: string) {
    setVisibleLines((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size > 1) next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  const activeLines = showIndividual ? LINE_CONFIGS : ASSET_AGGS;

  return (
    <div className={cardStyles.card}>
      <div className={cardStyles.cardTitle}>Performance &amp; Analysis</div>

      <div className={styles.twoCharts}>
        {/* Chart 1 */}
        <div className={styles.chartBox}>
          <div className={styles.chartHeader}>
            <div className={styles.chartTitle}>Strategy Growth Over Time</div>
            <div className={styles.toggleGroup}>
              {HOURS.map((h) => (
                <button
                  key={h}
                  className={`${styles.toggleBtn} ${selectedHours === h ? styles.toggleBtnActive : ""}`}
                  onClick={() => setSelectedHours(h)}
                >
                  {h}
                </button>
              ))}
            </div>
          </div>
          <div className={styles.chartMeta}>
            <span className={styles.chartMetaVal} style={{ color: "var(--green)" }}>
              {growthData.length > 0 ? `+${growthData[growthData.length - 1].pct.toFixed(1)}%` : ""}
            </span>
            <span className={styles.chartMetaLabel}>total return</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={growthData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0edf8" />
              <XAxis dataKey="x" hide />
              <YAxis
                tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
                tick={{ fontSize: 10, fill: "#9ca3af", fontFamily: "Roboto Mono" }}
                width={48}
              />
              <Tooltip content={<CustomTooltip1 />} />
              <Line
                type="monotone"
                dataKey="val"
                stroke="#7c3aed"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: "#7c3aed" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Chart 2 */}
        <div className={styles.chartBox}>
          <div className={styles.chartHeader}>
            <div className={styles.chartTitle}>Performance Across Markets</div>
            <button
              className={`${styles.toggleBtn} ${showIndividual ? styles.toggleBtnActive : ""}`}
              onClick={() => {
                setShowIndividual(!showIndividual);
                setVisibleLines(new Set(showIndividual ? ASSET_AGGS.map((a) => a.key) : LINE_CONFIGS.map((l) => l.key)));
              }}
            >
              {showIndividual ? "Aggregated" : "All 9 lines"}
            </button>
          </div>
          <div className={styles.legendRow}>
            {activeLines.map((l) => (
              <button
                key={l.key}
                className={`${styles.legendBtn} ${!visibleLines.has(l.key) ? styles.legendBtnFaded : ""}`}
                onClick={() => toggleLine(l.key)}
              >
                <span className={styles.legendDot} style={{ background: l.color }} />
                {l.label}
              </button>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={perf2} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0edf8" />
              <XAxis dataKey="x" hide />
              <YAxis
                tickFormatter={(v) => `${v >= 0 ? "+" : ""}${v.toFixed(0)}%`}
                tick={{ fontSize: 10, fill: "#9ca3af", fontFamily: "Roboto Mono" }}
                width={48}
              />
              <Tooltip content={<CustomTooltip2 />} />
              {activeLines.map((l) =>
                visibleLines.has(l.key) ? (
                  <Line
                    key={l.key}
                    type="monotone"
                    dataKey={l.key}
                    name={l.label}
                    stroke={l.color}
                    strokeWidth={showIndividual ? 1.5 : 2}
                    dot={false}
                    activeDot={{ r: 3 }}
                  />
                ) : null
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
