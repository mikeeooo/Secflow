import { Pause, Play } from "lucide-react";
import { useStreamControl, useStreamStatus } from "../api/hooks";
import type { StreamStatus } from "../api/types";
import { errorMessage } from "./States";
import { Button, Segmented, cx } from "./ui";

const MODES: { value: StreamStatus["mode"]; label: string }[] = [
  { value: "continuous", label: "Every 2 s" },
  { value: "batch_5", label: "5 per batch" },
  { value: "batch_10", label: "10" },
  { value: "batch_20", label: "20" },
];

/**
 * Controls for the single backend-owned producer. These calls do not depend on the feed,
 * so Stop keeps working even while feed polling is failing.
 */
export function StreamControls({ compact = false, status: external }: { compact?: boolean; status?: StreamStatus }) {
  const query = useStreamStatus();
  const status = query.data ?? external;
  const { start, stop, mode } = useStreamControl();
  const running = status?.running ?? false;
  const failure = stop.error ?? start.error ?? mode.error;
  return (
    <div className="flex flex-col items-start gap-2 sm:items-end">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-surface px-3 py-1.5 text-[13px] font-medium shadow-[0_0_0_1px_var(--sf-separator)]">
          <span aria-hidden className={cx("size-2 rounded-full", running ? "bg-permit" : "bg-label-2")} />
          {status ? (running ? "Stream running" : "Stream stopped") : "Stream status unknown"}
        </span>
        {running ? (
          <Button variant="destructive" onClick={() => stop.mutate()} disabled={stop.isPending}>
            <Pause aria-hidden className="size-4" /> {stop.isPending ? "Stopping…" : "Stop"}
          </Button>
        ) : (
          <Button variant="primary" onClick={() => start.mutate()} disabled={start.isPending}>
            <Play aria-hidden className="size-4" /> {start.isPending ? "Starting…" : "Start"}
          </Button>
        )}
      </div>
      {!compact && status ? (
        <Segmented label="Stream pace" size="sm" value={status.mode} options={MODES} onChange={(value) => mode.mutate(value)} />
      ) : null}
      {failure ? (
        <p role="alert" className="text-[13px] text-block">
          {errorMessage(failure)}
          {running ? " Press Stop again to retry." : ""}
        </p>
      ) : null}
    </div>
  );
}
