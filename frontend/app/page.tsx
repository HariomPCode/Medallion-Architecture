import Link from "next/link";
import { ThemeToggle } from "@/components/theme-toggle";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="min-h-screen p-6 md:p-10 max-w-5xl mx-auto space-y-6">
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Finance Complaints Medallion
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Regulatory intelligence and complaint analytics workbench
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggle />
        </div>
      </header>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle>Frontend Foundation & Design System</CardTitle>
          <Badge variant="positive" dot>
            Phase 7 Active
          </Badge>
        </CardHeader>
        <CardContent className="space-y-3 pt-2">
          <p className="text-xs text-muted-foreground leading-relaxed">
            Phase 7, Day 2 design system established with IBM Plex typography, light and dark themes,
            accessible Financial Editorial tokens, and refined base UI primitives.
          </p>
          <div className="pt-2">
            <Link href="/design">
              <Button variant="outline" size="sm">
                View Design System Preview (/design)
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
