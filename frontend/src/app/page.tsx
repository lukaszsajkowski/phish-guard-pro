import { Shield, Zap, Eye, FileWarning } from "lucide-react";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Shield className="h-8 w-8 text-primary" />
            <span className="text-xl font-bold tracking-tight">
              PhishGuard Pro
            </span>
          </div>
          <nav className="flex items-center gap-4">
            <a
              href="/login"
              className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              Login
            </a>
            <a
              href="/register"
              className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Get Started
            </a>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1">
        <section className="container flex flex-col items-center justify-center gap-8 px-4 py-24 text-center md:py-32">
          <div className="inline-flex items-center rounded-full border border-border/50 bg-muted/50 px-4 py-1.5">
            <span className="text-xs font-medium text-muted-foreground">
              🛡️ Active Defense Against Phishing
            </span>
          </div>

          <h1 className="max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            Turn Phishing Attacks Into{" "}
            <span className="bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 bg-clip-text text-transparent">
              Threat Intel
            </span>
          </h1>

          <p className="max-w-2xl text-lg text-muted-foreground md:text-xl">
            Autonomous AI agents that engage scammers in believable
            conversation, waste their time, and extract valuable Indicators of
            Compromise — all while keeping you safe.
          </p>

          <div className="flex flex-col gap-4 sm:flex-row">
            <a
              href="/demo"
              className="inline-flex h-12 items-center justify-center gap-2 rounded-md bg-primary px-8 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              <Zap className="h-4 w-4" />
              Try Demo Mode
            </a>
            <a
              href="/register"
              className="inline-flex h-12 items-center justify-center rounded-md border border-border bg-background px-8 text-sm font-medium transition-colors hover:bg-muted"
            >
              Create Free Account
            </a>
          </div>
        </section>

        {/* Features Section */}
        <section className="container px-4 py-16">
          <div className="grid gap-8 md:grid-cols-3">
            <div className="rounded-xl border border-border/50 bg-card p-6">
              <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-lg bg-blue-500/10">
                <FileWarning className="h-6 w-6 text-blue-500" />
              </div>
              <h3 className="mb-2 text-lg font-semibold">
                Smart Classification
              </h3>
              <p className="text-sm text-muted-foreground">
                Automatically classify phishing emails into 8 attack categories
                with confidence scoring.
              </p>
            </div>

            <div className="rounded-xl border border-border/50 bg-card p-6">
              <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-lg bg-purple-500/10">
                <Shield className="h-6 w-6 text-purple-500" />
              </div>
              <h3 className="mb-2 text-lg font-semibold">Safe Engagement</h3>
              <p className="text-sm text-muted-foreground">
                AI personas engage scammers with fake data, never exposing your
                real information.
              </p>
            </div>

            <div className="rounded-xl border border-border/50 bg-card p-6">
              <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-lg bg-pink-500/10">
                <Eye className="h-6 w-6 text-pink-500" />
              </div>
              <h3 className="mb-2 text-lg font-semibold">
                Real-time Intel Extraction
              </h3>
              <p className="text-sm text-muted-foreground">
                Extract BTC wallets, IBANs, phone numbers, and malicious URLs
                automatically.
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/40 py-8">
        <div className="container flex flex-col items-center justify-between gap-4 px-4 md:flex-row">
          <p className="text-sm text-muted-foreground">
            © 2024 PhishGuard Pro. Built for security researchers.
          </p>
          <div className="flex gap-4">
            <a
              href="#"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Documentation
            </a>
            <a
              href="#"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
