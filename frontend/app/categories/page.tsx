import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function CategoriesPage() {
  return (
    <div className="space-y-6">
      <header className="border-b border-border pb-4">
        <h1 className="text-xl font-bold tracking-tight text-foreground">
          Category Analytics
        </h1>
        <p className="text-xs text-muted-foreground mt-1">
          Complaints volume, market share, and timely response compliance across product categories
        </p>
      </header>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle as="h2">Phase 8 Destination</CardTitle>
          <Badge variant="neutral" dot>
            Planned: Phase 8
          </Badge>
        </CardHeader>
        <CardContent className="space-y-2 pt-2 text-xs text-muted-foreground">
          <p>
            Category and sub-category analytics panels, comparison bar charts, and Year-over-Year
            trend tables are scheduled for implementation in Phase 8.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
