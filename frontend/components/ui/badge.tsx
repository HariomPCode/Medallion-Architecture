import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-[11px] font-medium transition-colors select-none",
  {
    variants: {
      variant: {
        default:
          "border border-transparent bg-primary text-primary-foreground",
        secondary:
          "border border-transparent bg-secondary text-secondary-foreground",
        positive:
          "border border-status-success/20 bg-status-success-bg text-status-success font-semibold",
        warning:
          "border border-status-warning/20 bg-status-warning-bg text-status-warning font-semibold",
        negative:
          "border border-status-error/20 bg-status-error-bg text-status-error font-semibold",
        neutral:
          "border border-status-neutral/20 bg-status-neutral-bg text-status-neutral font-medium",
        outline:
          "border border-border text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean;
}

function Badge({ className, variant, dot = false, children, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot && (
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full shrink-0",
            variant === "positive" && "bg-status-success",
            variant === "warning" && "bg-status-warning",
            variant === "negative" && "bg-status-error",
            variant === "neutral" && "bg-status-neutral",
            (!variant || variant === "default") && "bg-primary-foreground",
            variant === "secondary" && "bg-secondary-foreground",
            variant === "outline" && "bg-foreground"
          )}
          aria-hidden="true"
        />
      )}
      <span>{children}</span>
    </div>
  );
}

export { Badge, badgeVariants };
