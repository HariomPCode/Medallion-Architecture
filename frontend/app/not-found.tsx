import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { FileQuestion } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Card className="max-w-md w-full border-border text-center">
        <CardHeader className="flex flex-col items-center space-y-2 pb-2">
          <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center text-muted-foreground">
            <FileQuestion className="h-6 w-6" aria-hidden="true" />
          </div>
          <CardTitle as="h2">Page Not Found</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 pt-2">
          <p className="text-xs text-muted-foreground">
            The requested destination does not exist or has been moved.
          </p>
          <div>
            <Link href="/">
              <Button variant="default" size="sm">
                Return to Overview
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
