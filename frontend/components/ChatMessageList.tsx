"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowDown, Clock, FileDown, MessageCircle, RefreshCw } from "lucide-react";
import ConfirmActionCard from "@/components/ConfirmActionCard";
import EmptyState from "@/components/EmptyState";
import type { ActionView, UiChatMessage } from "@/lib/types";

type ChatMessageListProps = {
  messages: UiChatMessage[];
  activeAction: ActionView | null;
  onConfirm: () => Promise<void>;
  onCancel: () => Promise<void>;
  onRetry: (messageId: string) => void;
};

export default function ChatMessageList({
  messages,
  activeAction,
  onConfirm,
  onCancel,
  onRetry,
}: ChatMessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const atBottomRef = useRef(true);
  const prevCountRef = useRef(0);
  const [showJump, setShowJump] = useState(false);

  const scrollToBottom = useCallback((behavior: ScrollBehavior) => {
    const el = containerRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior });
    setShowJump(false);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    const sentinel = sentinelRef.current;
    if (!container || !sentinel) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        atBottomRef.current = entry.isIntersecting;
        if (entry.isIntersecting) setShowJump(false);
      },
      { root: container, rootMargin: "0px 0px 80px 0px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (messages.length === prevCountRef.current) return;
    const isFirstLoad = prevCountRef.current === 0;
    prevCountRef.current = messages.length;
    if (isFirstLoad) {
      scrollToBottom("auto"); // instant on first load
    } else if (atBottomRef.current) {
      scrollToBottom("smooth");
    } else {
      setShowJump(true);
    }
  }, [messages.length, scrollToBottom]);

  const pendingConfirmation = activeAction?.status === "pending_confirmation" ? activeAction : null;
  let confirmIndex = -1;
  if (pendingConfirmation) {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant" && messages[i].actionId === pendingConfirmation.id) {
        confirmIndex = i;
        break;
      }
    }
  }

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      <div
        ref={containerRef}
        className="flex flex-1 flex-col gap-2 overflow-y-auto px-4 py-3 [overscroll-behavior:contain]"
      >
        {messages.length === 0 && (
          <div className="py-6">
            <EmptyState
              Icon={MessageCircle}
              title="עוד אין הודעות"
              hint='כתבו מה קרה בעסק. לדוגמה: "קיבלתי 2800 מנועה על עיצוב לוגו בביט"'
            />
          </div>
        )}
        {messages.map((m, i) => (
          <div key={m.id} className="flex flex-col gap-1">
            <div
              className={
                m.role === "user"
                  ? `ms-auto max-w-[85%] whitespace-pre-wrap rounded-2xl bg-primary px-4 py-2.5 text-on-primary ${
                      m.sendStatus === "pending" ? "opacity-60" : ""
                    }`
                  : "me-auto max-w-[85%] whitespace-pre-wrap rounded-2xl border border-border bg-white px-4 py-2.5"
              }
            >
              {m.text}
            </div>
            {m.sendStatus === "pending" && (
              <span className="ms-auto flex items-center gap-1 text-xs text-foreground/50">
                <Clock size={12} aria-hidden />
                שולח...
              </span>
            )}
            {m.sendStatus === "failed" && (
              <button
                onClick={() => onRetry(m.id)}
                className="ms-auto flex min-h-12 items-center gap-1.5 text-sm font-medium text-destructive transition-transform duration-150 active:scale-[0.98]"
              >
                <RefreshCw size={16} aria-hidden />
                שליחה נכשלה — הקש לנסות שוב
              </button>
            )}
            {m.pdfUrl && (
              <a
                href={m.pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="me-auto mt-1 flex min-h-12 items-center gap-2 rounded-xl border border-border bg-white px-4 text-sm font-medium text-primary transition-transform duration-150 active:scale-[0.98]"
              >
                <FileDown size={18} aria-hidden />
                הורדת PDF
              </a>
            )}
            {i === confirmIndex && pendingConfirmation && (
              <div className="mt-1">
                <ConfirmActionCard
                  action={pendingConfirmation}
                  onConfirm={onConfirm}
                  onCancel={onCancel}
                />
              </div>
            )}
          </div>
        ))}
        {pendingConfirmation && confirmIndex === -1 && (
          <ConfirmActionCard action={pendingConfirmation} onConfirm={onConfirm} onCancel={onCancel} />
        )}
        <div ref={sentinelRef} className="h-px shrink-0" aria-hidden />
      </div>
      {showJump && (
        <button
          onClick={() => scrollToBottom("smooth")}
          className="absolute inset-x-0 bottom-3 z-10 mx-auto flex min-h-12 w-fit items-center gap-1.5 rounded-full border border-border bg-white px-4 text-sm font-medium text-primary shadow-md transition-transform duration-150 active:scale-[0.98]"
        >
          <ArrowDown size={18} aria-hidden />
          הודעות חדשות
        </button>
      )}
    </div>
  );
}
