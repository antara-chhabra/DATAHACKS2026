"use client";
import { useTheme } from "@/app/ThemeContext";
import styles from "./ThemeToggle.module.css";

export default function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      className={styles.toggle}
      onClick={toggle}
      aria-label="Toggle dark/light mode"
      title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
    >
      <span className={styles.icon}>{theme === "dark" ? "☀" : "◑"}</span>
      <span className={styles.label}>{theme === "dark" ? "Light" : "Dark"} Mode</span>
    </button>
  );
}
