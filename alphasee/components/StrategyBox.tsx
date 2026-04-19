import cardStyles from "./Card.module.css";
import styles from "./StrategyBox.module.css";

const STEPS = [
  {
    step: "01",
    title: "Data observation → BTC leads",
    body: "EDA showed BTC markets have 3× more order book depth, tightest spreads (4.2¢ avg), and highest tick frequency. This made BTC the primary directional trading asset.",
    color: "#f59e0b",
  },
  {
    step: "02",
    title: "Noise filtering → SOL excluded",
    body: "SOL volatility (σ=0.071) is 2.3× BTC's. Directional SOL trades consistently produced large individual losses despite a high win rate. Decision: disable directional SOL, keep it for arbitrage only.",
    color: "#ef4444",
  },
  {
    step: "03",
    title: "Multi-signal alignment → reduces false entries",
    body: "Single signals produced +2.1% on average; all-4-signal alignment produced 14× higher P&L per trade. We exploit this correlation structure to filter noise.",
    color: "#6366f1",
  },
  {
    step: "04",
    title: "Staleness guard → oracle arbitrage",
    body: "Chainlink oracle prices lag Binance real-time by up to 30 seconds. We detect this staleness to identify temporary mispricing in YES/NO markets.",
    color: "#8b5cf6",
  },
  {
    step: "05",
    title: "Cross-asset boost → correlated conviction",
    body: "When BTC and ETH momentum align (same direction), we reduce required edge threshold by 1¢. This increases trade frequency on high-confidence setups without loosening risk control.",
    color: "#10b981",
  },
];

export default function StrategyBox() {
  return (
    <div className={cardStyles.card}>
      <div className={cardStyles.cardTitle}>Strategy Rationale</div>
      <p className={styles.intro}>
        Every design choice traces directly back to a data observation. Here's why we built what we built.
      </p>

      <div className={styles.steps}>
        {STEPS.map((s, i) => (
          <div key={s.step} className={styles.step}>
            <div className={styles.stepLeft}>
              <div className={styles.stepNum} style={{ color: s.color, borderColor: s.color + "44" }}>
                {s.step}
              </div>
              {i < STEPS.length - 1 && <div className={styles.connector} />}
            </div>
            <div className={styles.stepContent}>
              <div className={styles.stepTitle} style={{ color: s.color }}>{s.title}</div>
              <p className={styles.stepBody}>{s.body}</p>
            </div>
          </div>
        ))}
      </div>

      <div className={styles.result}>
        <div className={styles.resultBar} style={{ background: "linear-gradient(90deg, #7c3aed, #10b981)" }} />
        <div>
          <div className={styles.resultTitle}>Result: +109% over full period, Sharpe 11.94</div>
          <div className={styles.resultSub}>
            Strategy complexity was kept intentionally minimal — each signal earns its place with quantified edge.
          </div>
        </div>
      </div>
    </div>
  );
}
