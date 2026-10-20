export default function HomePage() {
  return (
    <main className="min-h-screen p-8 max-w-5xl mx-auto">
      <header className="border-b border-border pb-4 mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Finance Complaints Medallion
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Regulatory intelligence and complaint analytics workbench
        </p>
      </header>
      <section
        aria-label="System Status"
        className="rounded-md border border-border p-6 bg-card text-card-foreground shadow-sm"
      >
        <h2 className="text-base font-semibold mb-2">Frontend Foundation</h2>
        <p className="text-sm text-muted-foreground">
          Phase 7, Day 1 scaffold initialized with Next.js App Router, strict
          TypeScript, Tailwind CSS, ESLint, Vitest, React Testing Library, MSW,
          and vitest-axe.
        </p>
      </section>
    </main>
  );
}
