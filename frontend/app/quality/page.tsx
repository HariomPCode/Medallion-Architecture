import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function QualityPage() {
  return (
    <div className="space-y-6">
      <header className="border-b border-border pb-4">
        <h1 className="text-xl font-bold tracking-tight text-foreground">
          Data Quality Center
        </h1>
        <p className="text-xs text-muted-foreground mt-1">
          Pipeline data quality score, dimension breakdown, anomaly observations, and model metadata
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
            The Data Quality Center featuring composite scoring decomposition, five dimension bars,
            anomaly tables, model run parameters, and transparent methodology disclosures is scheduled
            for Phase 9.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
