"use client";
import Link from "next/link";
import dynamic from "next/dynamic";
import DecisionEngine from "@/components/DecisionEngine";
import WhyStrategy from "@/components/WhyStrategy";
import Assets from "@/components/Assets";
import MarketSignals from "@/components/MarketSignals";
import Charts from "@/components/Charts";
import Insights from "@/components/Insights";
import EDA from "@/components/EDA";
import StrategyBox from "@/components/StrategyBox";
import ProbabilityEngine from "@/components/ProbabilityEngine";
import EnvironmentalImpact from "@/components/EnvironmentalImpact";
import CorrelationSignals from "@/components/CorrelationSignals";
import FallingCoins from "@/components/FallingCoins";
import styles from "./dashboard.module.css";

const Volatility3D = dynamic(() => import("@/components/Volatility3D"), { ssr: false });

export default function Dashboard() {
  return (
    <div className={styles.page}>
      <FallingCoins />

      <header className={styles.header}>
        <Link href="/" className={styles.logoLink}>
          <span className={styles.logo}>AlphaSee</span>
        </Link>
        <div className={styles.headerMeta}>
          <span className={styles.live}>● Live Strategy</span>
          <span className={styles.assets}>BTC · ETH · SOL</span>
        </div>
      </header>

      <main className={styles.grid}>
        {/* Row 1: Decision Engine (wide) + Why Strategy */}
        <div className={styles.colWide}>
          <DecisionEngine />
        </div>
        <div className={styles.colNarrow}>
          <WhyStrategy />
        </div>

        {/* Row 2: EDA + Strategy Box */}
        <div className={styles.colHalf}>
          <EDA />
        </div>
        <div className={styles.colHalf}>
          <StrategyBox />
        </div>

        {/* Row 3: Assets + Volatility 3D (placed next to assets) */}
        <div className={styles.colHalf}>
          <Assets />
        </div>
        <div className={styles.colHalf}>
          <Volatility3D />
        </div>

        {/* Row 4: Market Signals + Probability Engine */}
        <div className={styles.colHalf}>
          <MarketSignals />
        </div>
        <div className={styles.colHalf}>
          <ProbabilityEngine />
        </div>

        {/* Row 5: Charts (full width) */}
        <div className={styles.colFull}>
          <Charts />
        </div>

        {/* Row 6: Environmental Impact (full width) */}
        <div className={styles.colFull}>
          <EnvironmentalImpact />
        </div>

        {/* Row 7: Correlation Signals (full width) */}
        <div className={styles.colFull}>
          <CorrelationSignals />
        </div>

        {/* Row 8: Insights (full width) */}
        <div className={styles.colFull}>
          <Insights />
        </div>

        {/* Marimo/Sphinx CTA */}
        <div className={styles.colFull}>
          <div className={styles.marimoCta}>
            <div className={styles.marimoLeft}>
              <div className={styles.marimoTitle}>Explore this strategy interactively</div>
              <p className={styles.marimoDesc}>
                This analysis is fully reproducible and interactive via our Marimo notebook.
                Run the backtester live, tweak signals, and see real-time results — no installation needed.
              </p>
            </div>
            <div className={styles.marimoRight}>
              <a
                href="http://localhost:2718"
                target="_blank"
                rel="noopener noreferrer"
                className={styles.marimoBtn}
              >
                <span className={styles.marimoBtnIcon}>◎</span>
                Try it on Marimo / Sphinx
              </a>
              <div className={styles.marimoHint}>Reproducible · Interactive · No-code</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
