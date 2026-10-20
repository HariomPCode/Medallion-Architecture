import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="space-y-6">
      <header className="border-b border-border pb-4">
        <h1 className="text-xl font-bold tracking-tight text-foreground">
          Finance Complaints Overview
        </h1>
        <p className="text-xs text-muted-foreground mt-1">
          Regulatory intelligence and complaint analytics workbench
        </p>
      </header>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle as="h2">Phase 7: Frontend Foundation & Shell</CardTitle>
          <Badge variant="positive" dot>
            Shell Active
          </Badge>
        </CardHeader>
        <CardContent className="space-y-3 pt-2">
          <p className="text-xs text-muted-foreground leading-relaxed">
            The application shell, secure BFF proxy, typed API client, and URL-synchronized
            filter infrastructure are active. Full Overview analytics panels and charts
            will be assembled in Phase 8.
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Link href="/categories">
              <Button variant="outline" size="sm">
                Category Analytics
              </Button>
            </Link>
            <Link href="/explorer">
              <Button variant="outline" size="sm">
                Complaint Explorer
              </Button>
            </Link>
            <Link href="/quality">
              <Button variant="outline" size="sm">
                Data Quality
              </Button>
            </Link>
            <Link href="/assistant">
              <Button variant="outline" size="sm">
                AI Assistant
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
