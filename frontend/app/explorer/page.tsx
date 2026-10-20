import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function ExplorerPage() {
  return (
    <div className="space-y-6">
      <header className="border-b border-border pb-4">
        <h1 className="text-xl font-bold tracking-tight text-foreground">
          Complaint Explorer
        </h1>
        <p className="text-xs text-muted-foreground mt-1">
          Search, filter, and inspect record-level CFPB complaints with streaming CSV export
        </p>
      </header>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle as="h2">Phase 9 Destination</CardTitle>
          <Badge variant="neutral" dot>
            Planned: Phase 9
          </Badge>
        </CardHeader>
        <CardContent className="space-y-2 pt-2 text-xs text-muted-foreground">
          <p>
            The Complaint Explorer table with server-side sorting, pagination, slide-out complaint
            detail drawer, and streaming CSV export is scheduled for implementation in Phase 9.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
