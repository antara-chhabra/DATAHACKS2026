"use client";
import { useState } from "react";
import cardStyles from "./Card.module.css";
import styles from "./EDA.module.css";

const EDA_FINDINGS = [
  {
    metric: "Avg Spread",
    btc: "4.2¢",
    eth: "6.8¢",
    sol: "9.1¢",
    insight: "BTC markets are most liquid with tightest spreads, creating the cleanest signal-to-noise ratio for our strategy.",
    tag: "Liquidity",
    color: "#f59e0b",
  },
  {
    metric: "YES Price Dist.",
    btc: "μ=0.53",
    eth: "μ=0.51",
    sol: "μ=0.49",
    insight: "YES prices cluster slightly above 0.5 for BTC/ETH, suggesting a mild bullish bias in short-horizon Polymarket markets.",
    tag: "Pricing Bias",
    color: "#6366f1",
  },
  {
    metric: "Order Book Depth",
    btc: "2,840",
    eth: "1,920",
    sol: "980",
    insight: "BTC consistently shows 3× the order book depth of SOL, making large trades feasible without significant slippage.",
    tag: "Market Depth",
    color: "#8b5cf6",
  },
  {
    metric: "Volatility (σ)",
    btc: "0.031",
    eth: "0.048",
    sol: "0.071",
    insight: "SOL volatility is 2.3× that of BTC in 5-minute windows. This is why directional SOL trades are disabled — noise dominates signal.",
    tag: "Risk Profile",
    color: "#ef4444",
  },
  {
    metric: "Market Duration",
    btc: "~48h",
    eth: "~48h",
    sol: "~48h",
    insight: "All markets share 48h settlement windows with 5m/15m/1h sub-intervals, allowing multi-resolution signal stacking.",
    tag: "Structure",
    color: "#10b981",
  },
  {
    metric: "Tick Frequency",
    btc: "12/min",
    eth: "10/min",
    sol: "8/min",
    insight: "Higher BTC tick frequency allows finer-grained momentum detection, improving 5-minute market edge detection.",
    tag: "Data Quality",
    color: "#7c3aed",
  },
];

export default function EDA() {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div className={cardStyles.card}>
      <div className={cardStyles.cardTitle}>Exploratory Data Analysis</div>
      <p className={styles.intro}>
        Key patterns discovered in raw Polymarket order book data across BTC, ETH, and SOL markets.
      </p>

      <div className={styles.table}>
        <div className={styles.tableHeader}>
          <span>Metric</span>
          <span>BTC</span>
          <span>ETH</span>
          <span>SOL</span>
          <span>Insight</span>
        </div>
        {EDA_FINDINGS.map((row, i) => (
          <div key={row.metric}>
            <div
              className={`${styles.tableRow} ${expanded === i ? styles.tableRowExpanded : ""}`}
              onClick={() => setExpanded(expanded === i ? null : i)}
            >
              <span className={styles.metricLabel}>
                <span className={styles.metricDot} style={{ background: row.color }} />
                {row.metric}
              </span>
              <span className={styles.cell}>{row.btc}</span>
              <span className={styles.cell}>{row.eth}</span>
              <span className={styles.cell}>{row.sol}</span>
              <span className={styles.cellTag} style={{ color: row.color, background: row.color + "18" }}>
                {row.tag}
              </span>
            </div>
            {expanded === i && (
              <div className={styles.insightExpand} style={{ borderLeft: `3px solid ${row.color}` }}>
                <span className={styles.insightIcon}>◎</span>
                {row.insight}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className={styles.summary}>
        <div className={styles.summaryItem}>
          <span className={styles.summaryVal}>242,680</span>
          <span className={styles.summaryLabel}>Total ticks analyzed</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryVal}>3</span>
          <span className={styles.summaryLabel}>Assets × 3 intervals</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryVal}>80h</span>
          <span className={styles.summaryLabel}>Training window</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryVal}>22.97%</span>
          <span className={styles.summaryLabel}>Validation return</span>
        </div>
      </div>
    </div>
  );
}
