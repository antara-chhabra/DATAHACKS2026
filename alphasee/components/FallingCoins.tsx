"use client";
import { useEffect, useRef } from "react";
import styles from "./FallingCoins.module.css";

const COIN_SYMBOLS = ["₿", "Ξ", "◎", "₿", "Ξ", "◎", "₿", "Ξ", "◎", "₿", "Ξ", "◎"];
const COIN_COLORS = ["#f59e0b", "#6366f1", "#8b5cf6"];

interface Coin {
  x: number;
  y: number;
  size: number;
  speed: number;
  opacity: number;
  symbol: string;
  color: string;
  rotation: number;
  rotSpeed: number;
  drift: number;
}

export default function FallingCoins() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const coinsRef = useRef<Coin[]>([]);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    function resize() {
      if (!canvas) return;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener("resize", resize);

    function createCoin(forced = false): Coin {
      const idx = Math.floor(Math.random() * COIN_SYMBOLS.length);
      return {
        x: Math.random() * (canvas?.width ?? window.innerWidth),
        y: forced ? Math.random() * (canvas?.height ?? window.innerHeight) : -40,
        size: 8 + Math.random() * 14,
        speed: 0.4 + Math.random() * 0.8,
        opacity: 0.06 + Math.random() * 0.12,
        symbol: COIN_SYMBOLS[idx],
        color: COIN_COLORS[idx % COIN_COLORS.length],
        rotation: Math.random() * Math.PI * 2,
        rotSpeed: (Math.random() - 0.5) * 0.04,
        drift: (Math.random() - 0.5) * 0.3,
      };
    }

    // Initial coins spread across screen
    for (let i = 0; i < 40; i++) {
      coinsRef.current.push(createCoin(true));
    }

    function animate() {
      if (!canvas || !ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      coinsRef.current.forEach((coin, i) => {
        coin.y += coin.speed;
        coin.x += coin.drift;
        coin.rotation += coin.rotSpeed;

        if (coin.y > canvas.height + 60) {
          coinsRef.current[i] = createCoin(false);
        }

        ctx.save();
        ctx.translate(coin.x, coin.y);
        ctx.rotate(coin.rotation);
        ctx.globalAlpha = coin.opacity;
        ctx.font = `${coin.size}px serif`;
        ctx.fillStyle = coin.color;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(coin.symbol, 0, 0);
        ctx.restore();
      });

      // Occasionally add a new coin
      if (Math.random() < 0.03 && coinsRef.current.length < 60) {
        coinsRef.current.push(createCoin(false));
      }

      animRef.current = requestAnimationFrame(animate);
    }

    animate();

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(animRef.current);
    };
  }, []);

  return <canvas ref={canvasRef} className={styles.canvas} />;
}
