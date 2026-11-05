import { AlertTriangle, Inbox, RotateCw } from "lucide-react";
import type { ReactNode } from "react";
import { ApiError } from "../api/client";
import { Button } from "./ui";

export function LoadingState({ label = "Loading", rows = 4 }: { label?: string; rows?: number }) {
  return (
    <div role="status" aria-live="polite" className="space-y-3 p-5">
      <span className="sr-only">{label}…</span>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-4 animate-pulse rounded bg-surface-2" style={{ width: `${90 - i * 12}%` }} />
      ))}
    </div>
  );
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

export function ErrorState({ error, onRetry, title = "Couldn't load this view" }: { error: unknown; onRetry?: () => void; title?: string }) {
  return (
    <div role="alert" className="flex flex-col items-start gap-3 p-5 sm:flex-row sm:items-center">
      <AlertTriangle aria-hidden className="size-5 shrink-0 text-block" />
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{title}</p>
        <p className="text-[14px] text-label-2">{errorMessage(error)}</p>
      </div>
      {onRetry ? (
        <Button onClick={onRetry}>
          <RotateCw aria-hidden className="size-4" /> Try again
        </Button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-10 text-center">
      <Inbox aria-hidden className="size-7 text-label-2" />
      <p className="font-semibold">{title}</p>
      {children ? <p className="max-w-md text-[14px] text-label-2">{children}</p> : null}
      {action}
    </div>
  );
}
