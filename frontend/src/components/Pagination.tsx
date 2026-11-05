import { ChevronLeft, ChevronRight } from "lucide-react";
import { formatInt } from "../lib/format";
import { Button } from "./ui";

export function Pagination({ page, pageSize, total, onPage }: { page: number; pageSize: number; total: number; onPage: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(total, page * pageSize);
  return (
    <nav aria-label="Pagination" className="flex flex-wrap items-center justify-between gap-3 border-t border-separator px-5 py-3">
      <p className="tabular text-[13px] text-label-2">
        {formatInt(from)}–{formatInt(to)} of {formatInt(total)}
      </p>
      <div className="flex items-center gap-2">
        <Button variant="plain" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Previous page">
          <ChevronLeft aria-hidden className="size-4" /> Previous
        </Button>
        <span className="tabular text-[13px] text-label-2">
          Page {page} of {formatInt(pages)}
        </span>
        <Button variant="plain" disabled={page >= pages} onClick={() => onPage(page + 1)} aria-label="Next page">
          Next <ChevronRight aria-hidden className="size-4" />
        </Button>
      </div>
    </nav>
  );
}
