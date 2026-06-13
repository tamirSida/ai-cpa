"use client";

import { useRef, useState, type ChangeEvent } from "react";
import { Camera, ImageUp, Loader2 } from "lucide-react";
import { api } from "@/lib/apiClient";
import type { Expense } from "@/lib/types";

export default function UploadExpenseButton({ businessId, onUploaded }:
  { businessId: string; onUploaded: (e: Expense) => void }) {
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleFile(file: File) {
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const uploaded = await api<Expense>(`/businesses/${businessId}/expenses/upload`, { method: "POST", body: form });
      let result = uploaded;
      try { result = await api<Expense>(`/businesses/${businessId}/expenses/${uploaded.id}/extract`, { method: "POST" }); }
      catch { /* 502 extraction_failed: keep raw upload, user fills the fields in the review sheet */ }
      onUploaded(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "ההעלאה נכשלה, נסו שוב");
    } finally {
      setBusy(false);
      if (cameraRef.current) cameraRef.current.value = "";
      if (galleryRef.current) galleryRef.current.value = "";
    }
  }

  const onPick = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="flex flex-col gap-2">
      {/* accept="image/*" only — never add image/heic here (Safari 17+ re-encoding regression);
          iOS converts HEIC to JPEG automatically when accept is image/* */}
      <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={onPick} />
      <input ref={galleryRef} type="file" accept="image/*" className="hidden" onChange={onPick} />
      <div className="flex gap-2">
        <button
          onClick={() => cameraRef.current?.click()}
          disabled={busy}
          className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          {busy ? <Loader2 size={20} className="animate-spin" aria-hidden /> : <Camera size={20} aria-hidden />}
          {busy ? "מעלה ומזהה..." : "צילום הוצאה"}
        </button>
        <button
          onClick={() => galleryRef.current?.click()}
          disabled={busy}
          className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl border border-border bg-white px-5 font-medium text-foreground transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          <ImageUp size={20} aria-hidden />
          העלאה מהגלריה
        </button>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
