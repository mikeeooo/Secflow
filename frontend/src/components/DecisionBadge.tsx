import { Ban, CircleCheck, Hourglass, ShieldAlert } from "lucide-react";
import type { DecisionLabel } from "../api/types";
import { cx } from "./ui";

export const LABEL_STYLE: Record<DecisionLabel, { tone: string; soft: string; Icon: typeof Ban }> = {
  Permitted: { tone: "text-permit", soft: "bg-permit-soft", Icon: CircleCheck },
  "Needs verification": { tone: "text-verify", soft: "bg-verify-soft", Icon: Hourglass },
  "Preventive risk block": { tone: "text-block", soft: "bg-block-soft", Icon: Ban },
  // Solid inverse badge: authoritative, and distinct from the red preventive block without another hue.
  "Confirmed fraud evidence": { tone: "text-surface", soft: "bg-evidence", Icon: ShieldAlert },
};

/** Decision label with an icon and text: the meaning never depends on colour alone. */
export function DecisionBadge({ label, size = "md" }: { label: DecisionLabel; size?: "sm" | "md" }) {
  const style = LABEL_STYLE[label];
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded-full font-semibold whitespace-nowrap",
        style.tone,
        style.soft,
        size === "sm" ? "px-2 py-0.5 text-[12px]" : "px-2.5 py-1 text-[13px]",
      )}
    >
      <style.Icon aria-hidden className={size === "sm" ? "size-3.5" : "size-4"} strokeWidth={2.2} />
      {label}
    </span>
  );
}
