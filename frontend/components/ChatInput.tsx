"use client";

import { useRef, useState } from "react";
import { Loader2, Send } from "lucide-react";

type ChatInputProps = {
  onSend: (text: string) => void;
  disabled: boolean;
};

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const autoGrow = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  };

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    setText("");
    const el = textareaRef.current;
    if (el) el.style.height = "auto";
    onSend(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const isMobile = window.matchMedia("(pointer: coarse)").matches;
    if (e.key === "Enter" && !e.shiftKey && !isMobile) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex items-end gap-2 bg-muted px-4 pb-2 pt-1">
      <textarea
        ref={textareaRef}
        value={text}
        rows={1}
        aria-label="הודעה"
        placeholder="מה קרה בעסק?"
        onChange={(e) => {
          setText(e.target.value);
          autoGrow();
        }}
        onKeyDown={handleKeyDown}
        className="min-h-12 flex-1 resize-none rounded-2xl border border-border bg-white px-4 py-3 text-base focus:outline-none focus:ring-2 focus:ring-primary"
      />
      <button
        onClick={submit}
        onMouseDown={(e) => e.preventDefault()}
        disabled={disabled || !text.trim()}
        aria-label="שליחה"
        className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
      >
        {disabled ? (
          <Loader2 size={20} className="animate-spin" aria-hidden />
        ) : (
          <Send size={20} className="-scale-x-100" aria-hidden />
        )}
      </button>
    </div>
  );
}
