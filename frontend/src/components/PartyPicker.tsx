import { Search } from "lucide-react";
import { useEffect, useId, useState } from "react";
import { api } from "../api/client";
import type { PartyOption } from "../api/types";
import { cx, inputClass } from "./ui";

/** Searchable combobox over named accounts (and, optionally, external counterparties). */
export function PartyPicker({
  id,
  value,
  onChange,
  accountsOnly = false,
  placeholder,
  invalid,
}: {
  id: string;
  value: PartyOption | null;
  onChange: (party: PartyOption | null) => void;
  accountsOnly?: boolean;
  placeholder: string;
  invalid?: boolean;
}) {
  const [text, setText] = useState(value?.name ?? "");
  const [options, setOptions] = useState<PartyOption[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [failed, setFailed] = useState(false);
  const listId = useId();

  useEffect(() => setText(value?.name ?? ""), [value]);

  useEffect(() => {
    if (!open) return;
    const handle = window.setTimeout(() => {
      api
        .parties(text, 12)
        .then((found) => {
          setFailed(false);
          setOptions(accountsOnly ? found.filter((o) => o.kind === "account") : found);
          setActive(0);
        })
        .catch(() => setFailed(true));
    }, 180);
    return () => window.clearTimeout(handle);
  }, [text, open, accountsOnly]);

  const choose = (option: PartyOption) => {
    onChange(option);
    setText(option.name);
    setOpen(false);
  };

  return (
    <div className="relative">
      <Search aria-hidden className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-label-2" />
      <input
        id={id}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-invalid={invalid || undefined}
        aria-activedescendant={open && options[active] ? `${listId}-${active}` : undefined}
        autoComplete="off"
        className={cx(inputClass, "pl-9", invalid && "border-block")}
        placeholder={placeholder}
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setOpen(true);
          if (value) onChange(null);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 120)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setActive((i) => Math.min(i + 1, options.length - 1));
          } else if (event.key === "ArrowUp") {
            event.preventDefault();
            setActive((i) => Math.max(i - 1, 0));
          } else if (event.key === "Enter" && open && options[active]) {
            event.preventDefault();
            choose(options[active]);
          } else if (event.key === "Escape") {
            setOpen(false);
          }
        }}
      />
      {open ? (
        <ul id={listId} role="listbox" className="absolute z-20 mt-1 max-h-72 w-full overflow-auto rounded-[12px] bg-surface p-1 shadow-xl ring-1 ring-separator">
          {failed ? <li className="px-3 py-2 text-[14px] text-block">Search is unavailable. Try again.</li> : null}
          {!failed && options.length === 0 ? <li className="px-3 py-2 text-[14px] text-label-2">No matches</li> : null}
          {options.map((option, index) => (
            <li
              key={option.id}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === active}
              onMouseDown={(event) => {
                event.preventDefault();
                choose(option);
              }}
              className={cx("flex cursor-pointer items-center justify-between gap-3 rounded-[8px] px-3 py-2", index === active && "bg-accent-soft")}
            >
              <span className="truncate text-[15px] font-medium">{option.name}</span>
              <span className="shrink-0 text-[12px] text-label-2">
                {option.id} · {option.kind === "account" ? option.detail : "external"}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
