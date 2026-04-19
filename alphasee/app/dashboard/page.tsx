"use client";
import { useState } from "react";
import Link from "next/link";
import DecisionEngine from "@/components/DecisionEngine";
import WhyStrategy from "@/components/WhyStrategy";
import Assets from "@/components/Assets";
import MarketSignals from "@/components/MarketSignals";
import Charts from "@/components/Charts";
import Insights from "@/components/Insights";
import styles from "./dashboard.module.css";

export default function Dashboard() {
  return (
    <div className={styles.page}>
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

        {/* Row 2: Assets + Market Signals */}
        <div className={styles.colHalf}>
          <Assets />
        </div>
        <div className={styles.colHalf}>
          <MarketSignals />
        </div>

        {/* Row 3: Charts (full width) */}
        <div className={styles.colFull}>
          <Charts />
        </div>

        {/* Row 4: Insights (full width) */}
        <div className={styles.colFull}>
          <Insights />
        </div>
      </main>
    </div>
  );
}
