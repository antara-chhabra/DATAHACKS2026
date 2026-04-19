"use client";
import Link from "next/link";
import FallingCoins from "@/components/FallingCoins";
import styles from "./page.module.css";

export default function LandingPage() {
  return (
    <div className={styles.landing}>
      {/* Animated background coins */}
      <FallingCoins />

      {/* Large decorative coin images */}
      <div className={styles.bgImages}>
        <div className={`${styles.coinWrap} ${styles.coinWrapBtc}`}>
          <img src="/btc.svg" alt="" className={`${styles.coinBg} ${styles.coinBtc}`} />
          <span className={styles.coinLabel}>BTC</span>
        </div>
        <div className={`${styles.coinWrap} ${styles.coinWrapEth}`}>
          <img src="/eth.svg" alt="" className={`${styles.coinBg} ${styles.coinEth}`} />
          <span className={styles.coinLabel}>ETH</span>
        </div>
        <div className={`${styles.coinWrap} ${styles.coinWrapSol}`}>
          <img src="/sol.svg" alt="" className={`${styles.coinBg} ${styles.coinSol}`} />
          <span className={styles.coinLabel}>SOL</span>
        </div>
      </div>

      {/* Center content */}
      <div className={styles.hero}>
        <div className={styles.badge}>Multi-Signal Trading Strategy</div>
        <h1 className={styles.title}>AlphaSee</h1>
        <p className={styles.sub}>
          We don't predict the market —<br />
          we wait for it to agree with itself.
        </p>
        <Link href="/dashboard" className={styles.cta}>
          Let's explore →
        </Link>
        <div className={styles.stats}>
          <div className={styles.stat}>
            <span className={styles.statVal}>+109%</span>
            <span className={styles.statLabel}>Full-period return</span>
          </div>
          <div className={styles.statDivider} />
          <div className={styles.stat}>
            <span className={styles.statVal}>11.94</span>
            <span className={styles.statLabel}>Sharpe ratio</span>
          </div>
          <div className={styles.statDivider} />
          <div className={styles.stat}>
            <span className={styles.statVal}>72.2%</span>
            <span className={styles.statLabel}>Win rate</span>
          </div>
        </div>

        {/* Coin showcase row */}
        <div className={styles.coinRow}>
          {[
            { img: "/btc.svg", name: "Bitcoin", ticker: "BTC", pnl: "+11.68%", color: "#f59e0b" },
            { img: "/eth.svg", name: "Ethereum", ticker: "ETH", pnl: "+0.15%", color: "#6366f1" },
            { img: "/sol.svg", name: "Solana", ticker: "SOL", pnl: "-0.36%", color: "#8b5cf6" },
          ].map((c) => (
            <div key={c.ticker} className={styles.coinChip} style={{ "--coin-color": c.color } as React.CSSProperties}>
              <img src={c.img} alt={c.name} className={styles.chipImg} />
              <div>
                <div className={styles.chipTicker}>{c.ticker}</div>
                <div className={styles.chipPnl} style={{ color: c.pnl.startsWith("+") ? "var(--green)" : "var(--red)" }}>{c.pnl}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
