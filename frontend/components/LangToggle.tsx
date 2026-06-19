"use client";

import { useI18n } from "@/lib/i18n";
import type { Lang } from "@/lib/messages";

const LANGS: Lang[] = ["en", "he"];

export default function LangToggle({ className = "" }: { className?: string }) {
  const { lang, setLang } = useI18n();
  return (
    <div className={`inline-flex rounded-xl border border-border bg-muted p-1 ${className}`} role="group" aria-label="Language">
      {LANGS.map((l) => (
        <button
          key={l}
          type="button"
          onClick={() => setLang(l)}
          aria-pressed={lang === l}
          className={`min-h-9 rounded-lg px-3 text-sm font-medium transition-colors ${
            lang === l ? "bg-white text-foreground shadow-sm" : "text-foreground/55"
          }`}
        >
          {l === "en" ? "English" : "עברית"}
        </button>
      ))}
    </div>
  );
}
