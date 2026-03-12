import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type StatusVariant = "active" | "inactive" | "pending" | "error";

interface StatusBadgeProps {
  status: StatusVariant | boolean;
  label?: string;
  className?: string;
}

const variantMap: Record<StatusVariant, { className: string; label: string }> = {
  active: {
    className: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20 dark:text-emerald-400",
    label: "Active",
  },
  inactive: {
    className: "bg-zinc-500/10 text-zinc-600 border-zinc-500/20 dark:text-zinc-400",
    label: "Inactive",
  },
  pending: {
    className: "bg-amber-500/10 text-amber-600 border-amber-500/20 dark:text-amber-400",
    label: "Pending",
  },
  error: {
    className: "bg-red-500/10 text-red-600 border-red-500/20 dark:text-red-400",
    label: "Error",
  },
};

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const variant: StatusVariant =
    typeof status === "boolean" ? (status ? "active" : "inactive") : status;

  const config = variantMap[variant];

  return (
    <Badge
      variant="outline"
      className={cn("font-medium", config.className, className)}
    >
      {label ?? config.label}
    </Badge>
  );
}
