import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetBrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PhishGuard Pro - AI-Powered Phishing Defense",
  description:
    "Autonomous agent-based system for active defense against phishing attacks. Engage scammers, waste their time, and extract threat intel.",
  keywords: [
    "phishing",
    "security",
    "AI",
    "threat intelligence",
    "scam",
    "defense",
  ],
};

/**
 * Inline script to prevent flash of wrong theme on load.
 * Reads localStorage before React hydrates and applies .dark class immediately.
 */
const themeScript = `
(function() {
  try {
    var theme = localStorage.getItem('pg_theme');
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body
        className={`${inter.variable} ${jetBrainsMono.variable} font-sans antialiased min-w-[1024px]`}
      >
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
