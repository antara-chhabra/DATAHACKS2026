"use client";
import { useState } from "react";
import styles from "./DecisionEngine.module.css";
import cardStyles from "./Card.module.css";

const SIGNALS = [
  {
    id: "price",
    label: "Real Price",
    source: "Chainlink",
    desc: "BTC oracle price exceeds market open — directional drift confirmed.",
    defaultActive: true,
  },
  {
    id: "momentum",
    label: "Momentum",
    source: "Binance",
    desc: "20-tick Binance mid-price rising faster than threshold.",
    defaultActive: true,
  },
  {
    id: "odds",
    label: "Market Odds",
    source: "Polymarket",
    desc: "Prediction market pricing creates edge vs. fair probability.",
    defaultActive: false,
  },
  {
    id: "agreement",
    label: "Cross-Asset Agreement",
    source: "BTC · ETH · SOL",
    desc: "BTC and ETH momentum aligned — correlated direction boost active.",
    defaultActive: true,
  },
];

export default function DecisionEngine() {
  const [active, setActive] = useState<Record<string, boolean>>(
    Object.fromEntries(SIGNALS.map((s) => [s.id, s.defaultActive]))
  );

  const activeCount = Object.values(active).filter(Boolean).length;
  const tradeSignal = activeCount === 4;

  return (
    <div className={cardStyles.card}>
      <div className={cardStyles.cardTitle}>Decision Engine</div>

      <div className={styles.signals}>
        {SIGNALS.map((sig) => (
          <button
            key={sig.id}
            className={`${styles.signal} ${active[sig.id] ? styles.signalActive : styles.signalInactive}`}
            onClick={() => setActive((prev) => ({ ...prev, [sig.id]: !prev[sig.id] }))}
          >
            <div className={styles.sigTop}>
              <div className={styles.sigLeft}>
                <span className={`${styles.dot} ${active[sig.id] ? styles.dotGreen : styles.dotGray}`} />
                <div>
                  <div className={styles.sigLabel}>{sig.label}</div>
                  <div className={styles.sigSource}>{sig.source}</div>
                </div>
              </div>
              <span className={`${styles.badge} ${active[sig.id] ? styles.badgeActive : styles.badgeInactive}`}>
                {active[sig.id] ? "ACTIVE" : "INACTIVE"}
              </span>
            </div>
            <div className={styles.sigDesc}>{sig.desc}</div>
          </button>
        ))}
      </div>

      <div className={styles.progress}>
        <div className={styles.progressHeader}>
          <span className={styles.progressLabel}>Signal Alignment</span>
          <span className={styles.progressCount}>{activeCount} / 4</span>
        </div>
        <div className={styles.progressBar}>
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className={`${styles.progressSeg} ${i < activeCount ? styles.progressSegFill : ""}`}
            />
          ))}
        </div>
      </div>

      <div className={`${styles.output} ${tradeSignal ? styles.outputYes : styles.outputNo}`}>
        {tradeSignal ? (
          <>
            <span className={styles.outputDot}>●</span>
            <div>
              <div className={styles.outputLabel}>TRADE SIGNAL: YES</div>
              <div className={styles.outputSub}>All 4 signals aligned — high-confidence entry</div>
            </div>
          </>
        ) : (
          <>
            <span className={styles.outputDotGray}>●</span>
            <div>
              <div className={styles.outputLabel}>NO TRADE</div>
              <div className={styles.outputSub}>{4 - activeCount} signal{4 - activeCount !== 1 ? "s" : ""} missing — waiting for alignment</div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
