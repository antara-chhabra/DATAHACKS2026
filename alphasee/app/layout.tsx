import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "./ThemeContext";
import ThemeToggle from "@/components/ThemeToggle";

export const metadata: Metadata = {
  title: "AlphaSee",
  description: "We don't predict the market — we wait for it to agree with itself.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" style={{ height: "100%" }}>
      <body style={{ minHeight: "100%", display: "flex", flexDirection: "column" }}>
        <ThemeProvider>
          {children}
          <ThemeToggle />
        </ThemeProvider>
      </body>
    </html>
  );
}
