"use client";
import Link from "next/link";
import styles from "./page.module.css";

export default function LandingPage() {
  return (
    <div className={styles.landing}>
      {/* Background coin images */}
      <div className={styles.bgImages}>
        <img src="/btc.svg" alt="" className={`${styles.coinBg} ${styles.coinBtc}`} />
        <img src="/eth.svg" alt="" className={`${styles.coinBg} ${styles.coinEth}`} />
        <img src="/sol.svg" alt="" className={`${styles.coinBg} ${styles.coinSol}`} />
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
      </div>
    </div>
  );
}
