"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { useT } from "@/lib/i18n";

type SheetProps = {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
};

export default function Sheet({ open, onClose, title, children }: SheetProps) {
  const t = useT();
  const panelRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  useEffect(() => { onCloseRef.current = onClose; });
  useEffect(() => {
    if (!open) return;
    const prevFocus = document.activeElement as HTMLElement | null;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onCloseRef.current(); };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    // move focus into the panel for screen-reader/keyboard users
    panelRef.current?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      prevFocus?.focus?.();
    };
  }, [open]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={title || undefined}>
      <button aria-label={t("common.close")} className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div ref={panelRef} tabIndex={-1} className="absolute inset-x-0 bottom-0 max-h-[85dvh] overflow-y-auto rounded-t-2xl bg-white p-4 pb-[calc(env(safe-area-inset-bottom,0px)+1rem)]">
        <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-border" aria-hidden />
        {title && (
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">{title}</h2>
            <button
              onClick={onClose}
              aria-label={t("common.close")}
              className="flex size-12 items-center justify-center text-foreground/55"
            >
              <X size={22} />
            </button>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
