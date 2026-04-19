"use client";
import { useState } from "react";
import styles from "./Assets.module.css";
import cardStyles from "./Card.module.css";

const ASSETS = [
  {
    id: "btc",
    name: "Bitcoin",
    ticker: "BTC",
    img: "/btc.svg",
    color: "#f59e0b",
    bg: "#fffbeb",
    pnl: "+11.68%",
    sharpe: "10.34",
    winRate: "87.5%",
    traits: ["Most liquid market", "Leads directional trends", "Strongest strategy edge"],
    desc: "Bitcoin markets exhibit the clearest momentum patterns. Our BTC directional strategy sees an 87.5% win rate on 5m markets, making it the highest-confidence signal asset.",
  },
  {
    id: "eth",
    name: "Ethereum",
    ticker: "ETH",
    img: "/eth.svg",
    color: "#6366f1",
    bg: "#eef2ff",
    pnl: "+0.15%",
    sharpe: "0.66",
    winRate: "72.7%",
    traits: ["Follows BTC trends", "Moderate edge", "Used for correlation signal"],
    desc: "ETH directional edge is thinner, but ETH price history is invaluable as a correlation filter. When ETH and BTC momentum align, we boost conviction on BTC trades.",
  },
  {
    id: "sol",
    name: "Solana",
    ticker: "SOL",
    img: "/sol.svg",
    color: "#8b5cf6",
    bg: "#f5f3ff",
    pnl: "-0.36%",
    sharpe: "-12.18",
    winRate: "100%",
    traits: ["Highest volatility", "Faster signal changes", "ARB opportunities only"],
    desc: "SOL directional signals are too noisy for reliable entries. The strategy deliberately disables directional SOL trading, using it only for arbitrage and as a volatility reference.",
  },
];

export default function Assets() {
  const [selected, setSelected] = useState<string | null>(null);

  const active = ASSETS.find((a) => a.id === selected);

  return (
    <div className={cardStyles.card}>
      <div className={cardStyles.cardTitle}>Assets</div>

      <div className={styles.cards}>
        {ASSETS.map((a) => (
          <button
            key={a.id}
            className={`${styles.assetCard} ${selected === a.id ? styles.assetCardSelected : ""}`}
            onClick={() => setSelected(selected === a.id ? null : a.id)}
            style={{ "--asset-color": a.color, "--asset-bg": a.bg } as React.CSSProperties}
          >
            <img src={a.img} alt={a.name} className={styles.coinImg} />
            <div className={styles.assetName}>{a.name}</div>
            <div className={styles.assetTicker}>{a.ticker}</div>
            <div className={styles.assetPnl} style={{ color: a.pnl.startsWith("+") ? "var(--green)" : "var(--red)" }}>
              {a.pnl}
            </div>
          </button>
        ))}
      </div>

      {active && (
        <div className={styles.detail} style={{ borderColor: active.color + "44", background: active.bg }}>
          <div className={styles.detailStats}>
            <div className={styles.dstat}>
              <span className={styles.dstatVal} style={{ color: active.color }}>{active.pnl}</span>
              <span className={styles.dstatLabel}>80h P&L</span>
            </div>
            <div className={styles.dstat}>
              <span className={styles.dstatVal}>{active.sharpe}</span>
              <span className={styles.dstatLabel}>Sharpe</span>
            </div>
            <div className={styles.dstat}>
              <span className={styles.dstatVal}>{active.winRate}</span>
              <span className={styles.dstatLabel}>Win Rate</span>
            </div>
          </div>
          <div className={styles.traits}>
            {active.traits.map((t) => (
              <span key={t} className={styles.trait} style={{ background: active.color + "22", color: active.color }}>
                {t}
              </span>
            ))}
          </div>
          <p className={styles.detailDesc}>{active.desc}</p>
        </div>
      )}

      {!active && (
        <p className={styles.hint}>Click an asset to explore its role in the strategy.</p>
      )}
    </div>
  );
}
