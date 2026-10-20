import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function AssistantPage() {
  return (
    <div className="space-y-6">
      <header className="border-b border-border pb-4">
        <h1 className="text-xl font-bold tracking-tight text-foreground">
          Grounded AI Assistant
        </h1>
        <p className="text-xs text-muted-foreground mt-1">
          Evidence-grounded analytical conversational assistant driven by verified backend tools
        </p>
      </header>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle as="h2">Phase 10 Destination</CardTitle>
          <Badge variant="neutral" dot>
            Planned: Phase 10
          </Badge>
        </CardHeader>
        <CardContent className="space-y-2 pt-2 text-xs text-muted-foreground">
          <p>
            The analytical chat interface, question composer with budget tracking, structured evidence
            cards, and verified numeric grounding displays are scheduled for Phase 10.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
