import styles from "./WhyStrategy.module.css";
import cardStyles from "./Card.module.css";

const PILLARS = [
  { icon: "⬡", label: "Real price movement", sub: "Chainlink oracle — ground truth" },
  { icon: "◈", label: "Market momentum", sub: "Binance order book confirmation" },
  { icon: "◎", label: "Prediction market pricing", sub: "Polymarket edge identification" },
  { icon: "◉", label: "Cross-asset agreement", sub: "BTC/ETH correlation filter" },
];

export default function WhyStrategy() {
  return (
    <div className={cardStyles.card}>
      <div className={cardStyles.cardTitle}>Why This Strategy?</div>

      <p className={styles.intro}>
        We only act when the market tells the same story in multiple ways.
      </p>

      <div className={styles.pillars}>
        {PILLARS.map((p) => (
          <div key={p.label} className={styles.pillar}>
            <span className={styles.icon}>{p.icon}</span>
            <div>
              <div className={styles.pillarLabel}>{p.label}</div>
              <div className={styles.pillarSub}>{p.sub}</div>
            </div>
          </div>
        ))}
      </div>

      <div className={styles.conclusion}>
        <div className={styles.conclusionBar} />
        <p>
          This reduces noise and focuses only on high-confidence opportunities —
          moments when price, momentum, market pricing, and cross-asset signals all point the same way.
        </p>
      </div>
    </div>
  );
}
