import styles from "./Insights.module.css";
import cardStyles from "./Card.module.css";

const INSIGHTS = [
  {
    stat: "+26.6%",
    title: "Signal alignment drives returns",
    desc: "The 80h run shows that when all 4 signals activate simultaneously, average trade P&L is 14× higher than single-signal entries. Alignment is rare but decisive.",
    tag: "Core finding",
    tagColor: "#7c3aed",
    tagBg: "#ede9fe",
  },
  {
    stat: "87.5%",
    title: "BTC 5m win rate — highest confidence",
    desc: "Across all asset-interval combinations, BTC 5-minute markets show the clearest mean reversion after oracle drift. Chainlink staleness guards are critical to this edge.",
    tag: "Market microstructure",
    tagColor: "#d97706",
    tagBg: "#fffbeb",
  },
  {
    stat: "−2.3%",
    title: "Momentum alone produces noisy trades",
    desc: "SOL directional trades on 15m and hourly intervals lost money despite 100% win rate — the few losses were large. This is why SOL directional trading is disabled.",
    tag: "Risk filter",
    tagColor: "#ef4444",
    tagBg: "#fef2f2",
  },
  {
    stat: "+0.01",
    title: "Cross-asset agreement improves edge",
    desc: "When BTC and ETH momentum point the same direction, we reduce the required edge threshold by 1 cent. This correlation boost increases trade frequency on high-confidence setups.",
    tag: "Signal interaction",
    tagColor: "#3b82f6",
    tagBg: "#eff6ff",
  },
  {
    stat: "+22.97%",
    title: "Out-of-sample validation holds",
    desc: "Validation data (unseen during strategy development) produced a +22.97% return vs. +26.57% in training — a small gap that suggests the strategy is not overfit to training patterns.",
    tag: "Validation",
    tagColor: "#10b981",
    tagBg: "#f0fdf4",
  },
  {
    stat: "3.57%",
    title: "Low drawdown across shorter windows",
    desc: "20h and 40h windows both see max drawdowns below 4%, showing the strategy is appropriately sized and doesn't chase losses. Only the 160h window sees elevated drawdown from market volatility.",
    tag: "Risk management",
    tagColor: "#6366f1",
    tagBg: "#eef2ff",
  },
];

export default function Insights() {
  return (
    <div className={cardStyles.card}>
      <div className={cardStyles.cardTitle}>Insights</div>
      <div className={styles.grid}>
        {INSIGHTS.map((ins) => (
          <div key={ins.title} className={styles.insight}>
            <div className={styles.insightTop}>
              <span className={styles.stat} style={{ color: ins.tagColor }}>{ins.stat}</span>
              <span className={styles.tag} style={{ color: ins.tagColor, background: ins.tagBg }}>{ins.tag}</span>
            </div>
            <div className={styles.title}>{ins.title}</div>
            <p className={styles.desc}>{ins.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
