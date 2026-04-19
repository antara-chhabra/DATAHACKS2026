"use client";
import { useState } from "react";
import styles from "./MarketSignals.module.css";
import cardStyles from "./Card.module.css";

const MARKETS = [
  { id: "5m", label: "5-minute", yes: 0.73, no: 0.21, edge: 0.06, active: true },
  { id: "15m", label: "15-minute", yes: 0.61, no: 0.35, edge: 0.04, active: true },
  { id: "1h", label: "1-hour", yes: 0.55, no: 0.42, edge: 0.03, active: false },
];

export default function MarketSignals() {
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <div className={cardStyles.card}>
      <div className={cardStyles.cardTitle}>Market Signals</div>

      <p className={styles.lead}>
        Prediction markets reflect probabilities, not certainty. Each YES price is the market's estimate that BTC will close above its opening price in the given window.
      </p>

      <div className={styles.markets}>
        {MARKETS.map((m) => (
          <div
            key={m.id}
            className={`${styles.market} ${hovered === m.id ? styles.marketHovered : ""}`}
            onMouseEnter={() => setHovered(m.id)}
            onMouseLeave={() => setHovered(null)}
          >
            <div className={styles.marketTop}>
              <div className={styles.marketLabel}>{m.label}</div>
              {m.active && <span className={styles.edgeBadge}>+{(m.edge * 100).toFixed(0)}¢ edge</span>}
              {!m.active && <span className={styles.noEdgeBadge}>thin</span>}
            </div>

            <div className={styles.barRow}>
              <span className={styles.barLabel}>YES</span>
              <div className={styles.barTrack}>
                <div className={styles.barFill} style={{ width: `${m.yes * 100}%`, background: "#10b981" }} />
              </div>
              <span className={`${styles.barVal} mono`}>{(m.yes * 100).toFixed(0)}¢</span>
            </div>

            <div className={styles.barRow}>
              <span className={styles.barLabel}>NO</span>
              <div className={styles.barTrack}>
                <div className={styles.barFill} style={{ width: `${m.no * 100}%`, background: "#ef4444" }} />
              </div>
              <span className={`${styles.barVal} mono`}>{(m.no * 100).toFixed(0)}¢</span>
            </div>

            {hovered === m.id && (
              <div className={styles.tooltip}>
                YES + NO = {((m.yes + m.no) * 100).toFixed(0)}¢ — arbitrage gap: {(m.edge * 100).toFixed(0)}¢
              </div>
            )}
          </div>
        ))}
      </div>

      <div className={styles.explainer}>
        <div className={styles.expItem}>
          <span className={styles.expIcon} style={{ color: "#10b981" }}>●</span>
          <span>YES price = probability BTC closes up</span>
        </div>
        <div className={styles.expItem}>
          <span className={styles.expIcon} style={{ color: "#ef4444" }}>●</span>
          <span>NO price = probability BTC closes down</span>
        </div>
        <div className={styles.expItem}>
          <span className={styles.expIcon} style={{ color: "var(--purple-dark)" }}>●</span>
          <span>YES + NO &lt; $1.00 = arbitrage opportunity</span>
        </div>
      </div>
    </div>
  );
}
