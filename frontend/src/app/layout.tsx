import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

const ibmPlexSans = IBM_Plex_Sans({
  variable: "--font-ibm-plex-sans",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
});

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
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
        className={`${ibmPlexSans.variable} ${ibmPlexMono.variable} font-sans antialiased min-w-[1024px]`}
      >
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
