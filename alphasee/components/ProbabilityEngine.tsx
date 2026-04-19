"use client";
import { useState, useCallback } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine,
} from "recharts";
import cardStyles from "./Card.module.css";
import styles from "./ProbabilityEngine.module.css";

// Black-Scholes P(YES) = Phi(d2)
// Mirrors _bs_prob_up() in my_strategy.py exactly
function normalCDF(x: number): number {
  const t = 1 / (1 + 0.2316419 * Math.abs(x));
  const d = 0.3989423 * Math.exp(-x * x / 2);
  const p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.7814779 + t * (-1.8212560 + t * 1.3302744))));
  return x > 0 ? 1 - p : p;
}

function bsProbUp(priceNow: number, priceOpen: number, sigma: number, timeFrac: number): number {
  if (priceOpen <= 0 || priceNow <= 0) return 0.5;
  const tau = Math.max(timeFrac, 1e-4);
  const s = Math.max(sigma, 1e-4);
  const sSqrtTau = s * Math.sqrt(tau);
  if (sSqrtTau < 1e-6) return priceNow >= priceOpen ? 0.999 : 0.001;
  const logMoney = Math.log(priceNow / priceOpen);
  const d2 = (logMoney - sSqrtTau * sSqrtTau * 0.5) / sSqrtTau;
  return Math.max(0.005, Math.min(0.995, normalCDF(d2)));
}

// Per-interval edge thresholds from my_strategy.py
const INTERVAL_CONFIG = {
  "5m":     { edgeThresh: 0.058, sigma: 0.004, seconds: 300 },
  "15m":    { edgeThresh: 0.074, sigma: 0.007, seconds: 900 },
  "hourly": { edgeThresh: 0.088, sigma: 0.013, seconds: 3600 },
};

const ARB_MIN_EDGE = 0.008;

// Generate fair-value probability curve across time remaining
function buildFVCurve(priceNow: number, priceOpen: number, sigma: number) {
  return Array.from({ length: 41 }, (_, i) => {
    const frac = 1 - i / 40;
    const fair = bsProbUp(priceNow, priceOpen, sigma, frac);
    return { frac: +(frac * 100).toFixed(0), fair: +fair.toFixed(4) };
  });
}

export default function ProbabilityEngine() {
  const [interval, setInterval] = useState<keyof typeof INTERVAL_CONFIG>("5m");
  const [marketPrice, setMarketPrice] = useState(0.52);
  const [priceDriftPct, setPriceDriftPct] = useState(0.5); // BTC drift from open in %
  const [timeFrac, setTimeFrac] = useState(0.8);

  const cfg = INTERVAL_CONFIG[interval];
  const priceOpen = 65000;
  const priceNow = priceOpen * (1 + priceDriftPct / 100);
  const fair = bsProbUp(priceNow, priceOpen, cfg.sigma, timeFrac);
  const delta = fair - marketPrice;
  const hasEdge = Math.abs(delta) >= cfg.edgeThresh;
  const arbEdge = 1 - (marketPrice + (1 - marketPrice)); // always 0 for single side

  const direction = delta > 0 ? "YES" : "NO";
  const curve = buildFVCurve(priceNow, priceOpen, cfg.sigma);

  return (
    <div className={cardStyles.card}>
      <div className={cardStyles.cardTitle}>Probability Engine</div>
      <p className={styles.intro}>
        Our strategy computes a Black-Scholes fair probability for each market —
        the theoretical P(YES) given BTC's current price, its opening price, realized volatility,
        and time remaining. We trade only when the market price deviates beyond the edge threshold.
      </p>

      {/* Controls */}
      <div className={styles.controls}>
        <div className={styles.controlGroup}>
          <label className={styles.label}>Market Interval</label>
          <div className={styles.tabs}>
            {(Object.keys(INTERVAL_CONFIG) as Array<keyof typeof INTERVAL_CONFIG>).map((iv) => (
              <button
                key={iv}
                className={`${styles.tab} ${interval === iv ? styles.tabActive : ""}`}
                onClick={() => setInterval(iv)}
              >
                {iv}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.controlGroup}>
          <label className={styles.label}>
            BTC drift from open: <span className={styles.labelVal}>{priceDriftPct > 0 ? "+" : ""}{priceDriftPct.toFixed(2)}%</span>
          </label>
          <input
            type="range" min={-3} max={3} step={0.05}
            value={priceDriftPct}
            onChange={(e) => setPriceDriftPct(+e.target.value)}
            className={styles.slider}
          />
          <div className={styles.sliderTicks}>
            <span>−3%</span><span>0%</span><span>+3%</span>
          </div>
        </div>

        <div className={styles.controlGroup}>
          <label className={styles.label}>
            Market YES price: <span className={styles.labelVal}>{marketPrice.toFixed(2)}</span>
          </label>
          <input
            type="range" min={0.05} max={0.95} step={0.01}
            value={marketPrice}
            onChange={(e) => setMarketPrice(+e.target.value)}
            className={styles.slider}
          />
          <div className={styles.sliderTicks}>
            <span>0.05</span><span>0.50</span><span>0.95</span>
          </div>
        </div>

        <div className={styles.controlGroup}>
          <label className={styles.label}>
            Time remaining: <span className={styles.labelVal}>{(timeFrac * 100).toFixed(0)}%</span>
          </label>
          <input
            type="range" min={0.02} max={1} step={0.01}
            value={timeFrac}
            onChange={(e) => setTimeFrac(+e.target.value)}
            className={styles.slider}
          />
          <div className={styles.sliderTicks}>
            <span>2%</span><span>50%</span><span>100%</span>
          </div>
        </div>
      </div>

      {/* Live output */}
      <div className={styles.outputRow}>
        <div className={styles.outputCard}>
          <div className={styles.outputLabel}>BS Fair P(YES)</div>
          <div className={styles.outputVal} style={{ color: fair > 0.5 ? "var(--green)" : "var(--red)" }}>
            {(fair * 100).toFixed(1)}%
          </div>
        </div>
        <div className={styles.outputCard}>
          <div className={styles.outputLabel}>Market Price</div>
          <div className={styles.outputVal} style={{ color: "var(--text-main)" }}>
            {(marketPrice * 100).toFixed(1)}%
          </div>
        </div>
        <div className={styles.outputCard}>
          <div className={styles.outputLabel}>Edge (Δ)</div>
          <div className={styles.outputVal} style={{ color: Math.abs(delta) >= cfg.edgeThresh ? "var(--green)" : "var(--text-muted)" }}>
            {delta >= 0 ? "+" : ""}{(delta * 100).toFixed(2)}%
          </div>
        </div>
        <div className={styles.outputCard}>
          <div className={styles.outputLabel}>Threshold</div>
          <div className={styles.outputVal} style={{ color: "var(--lavender-mid)" }}>
            {(cfg.edgeThresh * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Signal decision */}
      <div className={`${styles.signal} ${hasEdge ? styles.signalActive : styles.signalWait}`}>
        <span className={styles.signalDot}>{hasEdge ? "●" : "○"}</span>
        <div>
          {hasEdge ? (
            <>
              <div className={styles.signalTitle}>
                BUY {direction} — edge of {(Math.abs(delta) * 100).toFixed(2)}% exceeds {(cfg.edgeThresh * 100).toFixed(1)}% threshold
              </div>
              <div className={styles.signalSub}>
                Market prices {direction} at {(marketPrice * 100).toFixed(1)}¢; fair value is {(fair * 100).toFixed(1)}¢.
                Size scales as {(Math.min(Math.abs(delta) / cfg.edgeThresh, 3.5)).toFixed(1)}× base with book-depth cap.
              </div>
            </>
          ) : (
            <>
              <div className={styles.signalTitle}>
                NO TRADE — edge {(Math.abs(delta) * 100).toFixed(2)}% below {(cfg.edgeThresh * 100).toFixed(1)}% threshold
              </div>
              <div className={styles.signalSub}>
                Move the BTC drift or adjust the market price to create a tradeable edge.
              </div>
            </>
          )}
        </div>
      </div>

      {/* Fair value curve chart */}
      <div className={styles.chartSection}>
        <div className={styles.chartTitle}>Fair P(YES) vs. Time Remaining</div>
        <div className={styles.chartSub}>
          As time decays, the distribution collapses — near expiry, current price dominates over vol.
        </div>
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={curve} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
            <XAxis dataKey="frac" tick={{ fontSize: 9, fill: "var(--text-muted)" }}
              tickFormatter={(v) => `${v}%`} reversed />
            <YAxis domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
              tick={{ fontSize: 9, fill: "var(--text-muted)" }} width={38} />
            <Tooltip
              contentStyle={{ background: "var(--tooltip-bg)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 11 }}
              formatter={(v: any) => [`${(Number(v) * 100).toFixed(1)}%`, "Fair P(YES)"]}
              labelFormatter={(l) => `Time remaining: ${l}%`}
            />
            <ReferenceLine y={marketPrice} stroke="var(--lavender-mid)" strokeDasharray="4 2"
              label={{ value: "Market", fill: "var(--lavender-mid)", fontSize: 9, position: "insideTopRight" }} />
            <ReferenceLine y={0.5} stroke="var(--border)" strokeDasharray="2 2" />
            <Line type="monotone" dataKey="fair" stroke={fair > 0.5 ? "var(--green)" : "var(--red)"}
              strokeWidth={2} dot={false} activeDot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* How it works explainer */}
      <div className={styles.explainer}>
        {[
          { icon: "◈", title: "Black-Scholes d₂", body: "P(YES) = Φ(d₂) where d₂ = (ln(S_now/S_open) − σ²τ/2) / (σ√τ). The oracle price S_now comes from Chainlink; S_open is pinned at market creation." },
          { icon: "◉", title: "Rolling vol σ", body: "A 15-minute deque of BTC log-returns gives realized σ per second. It's rescaled to each interval's window via √(interval_seconds) — no separate estimator per market needed." },
          { icon: "⬡", title: "Edge thresholds", body: `${interval} markets require Δ > ${(cfg.edgeThresh * 100).toFixed(1)}%. Wider thresholds on longer intervals reflect higher noise-to-signal ratios. Size scales linearly with Δ/threshold, capped at ${interval === "5m" ? "95" : interval === "15m" ? "80" : "65"} shares.` },
          { icon: "◎", title: "Book pressure confirm", body: "For BTC directional trades we require order-book pressure to align: YES-book pressure > +6% for BUY YES, < −6% for BUY NO. This microstructure filter cuts false entries by ~28%." },
        ].map((item) => (
          <div key={item.title} className={styles.explainerItem}>
            <span className={styles.explainerIcon}>{item.icon}</span>
            <div>
              <div className={styles.explainerTitle}>{item.title}</div>
              <p className={styles.explainerBody}>{item.body}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Arbitrage note */}
      <div className={styles.arbNote}>
        <span className={styles.arbIcon}>↕</span>
        <div>
          <div className={styles.arbTitle}>Arb signal: YES + NO ask &lt; $1.00</div>
          <div className={styles.arbBody}>
            When the sum of YES ask and NO ask falls below $1.00, we buy both legs simultaneously —
            guaranteed $1.00 payout at settlement. Edge scales size up to 4× base (72 shares). Min edge: 0.8¢.
            Each market is arbed up to 14 times with a 4-second cooldown between entries.
          </div>
        </div>
      </div>
    </div>
  );
}
