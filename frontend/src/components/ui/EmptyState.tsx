import type { LucideIcon } from "lucide-react";
import Button from "./Button";
import Card from "./Card";

/** Empty state (spec 3.11): centered icon, title, one line, one button. */
export default function EmptyState({
  icon: Icon,
  title,
  line,
  actionLabel,
  onAction,
  actionVariant = "primary",
}: {
  icon: LucideIcon;
  title: string;
  line: string;
  actionLabel?: string;
  onAction?: () => void;
  actionVariant?: "primary" | "secondary";
}) {
  return (
    <Card className="py-8 text-center">
      <Icon size={40} strokeWidth={1.75} className="mx-auto text-text-3" aria-hidden />
      <h3 className="mt-3 text-[16px] font-semibold">{title}</h3>
      <p className="mt-1 text-[14px] text-text-2">{line}</p>
      {actionLabel && onAction && (
        <div className="mt-4 flex justify-center">
          <Button variant={actionVariant} onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      )}
    </Card>
  );
}
