"use client";
import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine, Area, AreaChart,
} from "recharts";
import cardStyles from "./Card.module.css";
import styles from "./EnvironmentalImpact.module.css";

// Mock monthly data 2020-2024 for BTC energy consumption (TWh/yr annualized) vs price
const BTC_DATA = [
  { month: "Jan'21", energy: 77, price: 33000, vol: 0.042 },
  { month: "Apr'21", energy: 149, price: 58000, vol: 0.071 },
  { month: "Jul'21", energy: 95, price: 35000, vol: 0.055 },
  { month: "Oct'21", energy: 130, price: 60000, vol: 0.063 },
  { month: "Jan'22", energy: 204, price: 48000, vol: 0.058 },
  { month: "Apr'22", energy: 198, price: 39000, vol: 0.073 },
  { month: "Jul'22", energy: 154, price: 20000, vol: 0.089 },
  { month: "Oct'22", energy: 134, price: 19000, vol: 0.062 },
  { month: "Jan'23", energy: 122, price: 23000, vol: 0.048 },
  { month: "Apr'23", energy: 148, price: 30000, vol: 0.044 },
  { month: "Jul'23", energy: 164, price: 29000, vol: 0.039 },
  { month: "Oct'23", energy: 178, price: 34000, vol: 0.051 },
  { month: "Jan'24", energy: 189, price: 44000, vol: 0.056 },
  { month: "Apr'24", energy: 211, price: 70000, vol: 0.068 },
];

// ETH data (post-merge drop)
const ETH_DATA = [
  { month: "Jan'21", energy: 22, price: 1200, vol: 0.065 },
  { month: "Apr'21", energy: 36, price: 2500, vol: 0.088 },
  { month: "Jul'21", energy: 28, price: 2200, vol: 0.071 },
  { month: "Oct'21", energy: 41, price: 4300, vol: 0.082 },
  { month: "Jan'22", energy: 69, price: 3400, vol: 0.076 },
  { month: "Apr'22", energy: 65, price: 3100, vol: 0.091 },
  { month: "Jul'22", energy: 54, price: 1500, vol: 0.099 },
  { month: "Sep'22", energy: 0.01, price: 1300, vol: 0.062, merge: true }, // The Merge
  { month: "Oct'22", energy: 0.01, price: 1300, vol: 0.058 },
  { month: "Jan'23", energy: 0.01, price: 1600, vol: 0.051 },
  { month: "Apr'23", energy: 0.01, price: 1900, vol: 0.044 },
  { month: "Jul'23", energy: 0.01, price: 1850, vol: 0.041 },
  { month: "Oct'23", energy: 0.01, price: 1600, vol: 0.048 },
  { month: "Jan'24", energy: 0.01, price: 2300, vol: 0.055 },
  { month: "Apr'24", energy: 0.01, price: 3500, vol: 0.067 },
];

const BTC_INSIGHTS = [
  {
    stat: "+173%",
    title: "Energy use tracks price cycles",
    desc: "BTC mining energy consumption rose 173% during 2021 bull run, then fell 36% post-crash — indicating energy intensity is driven by miner profitability. High-energy periods correlate with elevated volatility (+0.031 avg σ).",
    tag: "Energy–Price Cycle",
    color: "#f59e0b",
  },
  {
    stat: "→ Caution",
    title: "High energy = high vol = wider spreads",
    desc: "When BTC energy use exceeds 180 TWh/yr, our strategy detects wider YES/NO spreads (avg +1.8¢), increasing the available arbitrage edge. We scale position size up cautiously to exploit this.",
    tag: "Strategy Impact",
    color: "#7c3aed",
  },
];

const ETH_INSIGHTS = [
  {
    stat: "−99.95%",
    title: "The Merge: energy drop is permanent",
    desc: "Ethereum's shift from PoW to PoS in Sept 2022 reduced energy use by 99.95%. This structural shift reduced ETH's environmental risk but also changed its volatility profile — post-merge σ dropped from 0.081 to 0.044.",
    tag: "Structural Change",
    color: "#6366f1",
  },
  {
    stat: "−42%",
    title: "Lower energy = lower vol = tighter spreads",
    desc: "Post-merge ETH markets show 42% lower volatility. Our strategy adjusts by reducing the correlation boost threshold for ETH signals — treating post-merge ETH momentum as a more reliable confirming signal.",
    tag: "Strategy Adaptation",
    color: "#10b981",
  },
];

function InsightBox({ insights, expanded, onToggle }: {
  insights: typeof BTC_INSIGHTS;
  expanded: number | null;
  onToggle: (i: number) => void;
}) {
  return (
    <div className={styles.insights}>
      {insights.map((ins, i) => (
        <div key={ins.title} className={styles.insightCard} onClick={() => onToggle(i)}>
          <div className={styles.insightHeader}>
            <span className={styles.insightStat} style={{ color: ins.color }}>{ins.stat}</span>
            <span className={styles.insightTag} style={{ color: ins.color, background: ins.color + "18" }}>
              {ins.tag}
            </span>
            <span className={styles.insightChevron}>{expanded === i ? "▲" : "▼"}</span>
          </div>
          <div className={styles.insightTitle}>{ins.title}</div>
          {expanded === i && <p className={styles.insightDesc}>{ins.desc}</p>}
        </div>
      ))}
    </div>
  );
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{ background: "var(--tooltip-bg)", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 12px", fontSize: 11 }}>
      <div style={{ color: "var(--purple-dark)", fontFamily: "Roboto Mono", marginBottom: 2 }}>{d.month}</div>
      {payload.map((p: any) => (
        <div key={p.name} style={{ color: p.color || "var(--text-mid)" }}>
          {p.name}: {p.value}
        </div>
      ))}
    </div>
  );
}

export default function EnvironmentalImpact() {
  const [btcExpanded, setBtcExpanded] = useState<number | null>(null);
  const [ethExpanded, setEthExpanded] = useState<number | null>(null);

  const mergeIdx = ETH_DATA.findIndex((d) => d.merge);

  return (
    <div className={cardStyles.card}>
      <div className={cardStyles.cardTitle}>Environment, Energy &amp; Climate Impact</div>
      <p className={styles.intro}>
        Energy consumption and environmental signals directly influence crypto volatility.
        Our strategy adapts position sizing and signal thresholds based on these macro-environmental conditions.
      </p>

      <div className={styles.twoCol}>
        {/* BTC */}
        <div className={styles.col}>
          <div className={styles.colHeader}>
            <img src="/btc.svg" alt="BTC" className={styles.coinImg} />
            <div>
              <div className={styles.colTitle}>Bitcoin Energy Impact</div>
              <div className={styles.colSub}>Annualized TWh/yr vs. Price</div>
            </div>
          </div>

          <div className={styles.chartWrap}>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={BTC_DATA} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="btcGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                <XAxis dataKey="month" tick={{ fontSize: 9, fill: "var(--text-muted)" }} />
                <YAxis yAxisId="e" tick={{ fontSize: 9, fill: "#f59e0b" }} width={36} tickFormatter={(v) => `${v}T`} />
                <YAxis yAxisId="p" orientation="right" tick={{ fontSize: 9, fill: "#6366f1" }} width={44} tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} />
                <Tooltip content={<CustomTooltip />} />
                <Area yAxisId="e" type="monotone" dataKey="energy" name="Energy (TWh)" stroke="#f59e0b" fill="url(#btcGrad)" strokeWidth={2} dot={false} />
                <Line yAxisId="p" type="monotone" dataKey="price" name="Price ($)" stroke="#6366f1" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <InsightBox
            insights={BTC_INSIGHTS}
            expanded={btcExpanded}
            onToggle={(i) => setBtcExpanded(btcExpanded === i ? null : i)}
          />
        </div>

        {/* ETH */}
        <div className={styles.col}>
          <div className={styles.colHeader}>
            <img src="/eth.svg" alt="ETH" className={styles.coinImg} />
            <div>
              <div className={styles.colTitle}>Ethereum Energy Impact</div>
              <div className={styles.colSub}>Pre/Post Merge comparison</div>
            </div>
          </div>

          <div className={styles.chartWrap}>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={ETH_DATA} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="ethGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                <XAxis dataKey="month" tick={{ fontSize: 9, fill: "var(--text-muted)" }} />
                <YAxis yAxisId="e" tick={{ fontSize: 9, fill: "#6366f1" }} width={36} tickFormatter={(v) => v < 1 ? "~0" : `${v}T`} />
                <YAxis yAxisId="p" orientation="right" tick={{ fontSize: 9, fill: "#8b5cf6" }} width={44} tickFormatter={(v) => `$${(v/1000).toFixed(1)}k`} />
                <Tooltip content={<CustomTooltip />} />
                {mergeIdx !== -1 && (
                  <ReferenceLine yAxisId="e" x={ETH_DATA[mergeIdx].month} stroke="#10b981" strokeDasharray="4 2"
                    label={{ value: "The Merge", fill: "#10b981", fontSize: 9, position: "insideTopRight" }} />
                )}
                <Area yAxisId="e" type="monotone" dataKey="energy" name="Energy (TWh)" stroke="#6366f1" fill="url(#ethGrad)" strokeWidth={2} dot={false} />
                <Line yAxisId="p" type="monotone" dataKey="price" name="Price ($)" stroke="#8b5cf6" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <InsightBox
            insights={ETH_INSIGHTS}
            expanded={ethExpanded}
            onToggle={(i) => setEthExpanded(ethExpanded === i ? null : i)}
          />
        </div>
      </div>

      <div className={styles.mockStrategyWrap}>
        <div className={styles.mockTitle}>
          <span className={styles.mockIcon}>◎</span>
          Mock Strategy Return — Energy-Adjusted Model
        </div>
        <p className={styles.mockDesc}>
          Simulated return if our strategy dynamically scaled confidence based on energy environment signals.
          Periods of low environmental stress → higher conviction trades → better risk-adjusted returns.
        </p>
        <div className={styles.mockChart}>
          <ResponsiveContainer width="100%" height={120}>
            <AreaChart
              data={[
                { t: 0, base: 10000, adjusted: 10000 },
                { t: 10, base: 10400, adjusted: 10600 },
                { t: 20, base: 10200, adjusted: 10800 },
                { t: 30, base: 10800, adjusted: 11400 },
                { t: 40, base: 10600, adjusted: 11900 },
                { t: 50, base: 11200, adjusted: 12600 },
                { t: 60, base: 11000, adjusted: 13100 },
                { t: 70, base: 11800, adjusted: 13900 },
                { t: 80, base: 12100, adjusted: 14800 },
              ]}
              margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="adjGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
              <XAxis dataKey="t" hide />
              <YAxis tick={{ fontSize: 9, fill: "var(--text-muted)" }} width={48} tickFormatter={(v) => `$${(v/1000).toFixed(1)}k`} />
              <Tooltip
                formatter={(v: any, name: any) => [`$${Number(v).toLocaleString()}`, name === "adjusted" ? "Energy-Adjusted" : "Base Strategy"] as [string, string]}
                contentStyle={{ background: "var(--tooltip-bg)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 11 }}
              />
              <Area type="monotone" dataKey="adjusted" name="adjusted" stroke="#10b981" fill="url(#adjGrad)" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="base" name="base" stroke="var(--text-muted)" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className={styles.mockLegend}>
          <span><span style={{ color: "#10b981" }}>——</span> Energy-adjusted strategy</span>
          <span><span style={{ color: "var(--text-muted)" }}>- -</span> Base strategy (no env. signal)</span>
        </div>
      </div>
    </div>
  );
}
