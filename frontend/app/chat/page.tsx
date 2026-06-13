"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ChatInput from "@/components/ChatInput";
import ChatMessageList from "@/components/ChatMessageList";
import { api, ApiError } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { useIosKeyboardFix } from "@/lib/useIosKeyboardFix";
import type {
  ActionView,
  Business,
  ChatHistoryResponse,
  ChatTurnResult,
  UiChatMessage,
} from "@/lib/types";

let localIdCounter = 0;
const nextLocalId = (prefix: string) => `${prefix}-${Date.now()}-${localIdCounter++}`;

export default function ChatPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  useIosKeyboardFix();

  const [biz, setBiz] = useState<Business | null>(null);
  const [messages, setMessages] = useState<UiChatMessage[]>([]);
  const [activeAction, setActiveAction] = useState<ActionView | null>(null);
  const [sending, setSending] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  const pushAssistant = useCallback((text: string, extra?: Partial<UiChatMessage>) => {
    setMessages((prev) => [
      ...prev,
      { id: nextLocalId("a"), role: "assistant", text, createdAt: new Date().toISOString(), ...extra },
    ]);
  }, []);

  const pushError = useCallback(
    (e: unknown) => {
      pushAssistant(e instanceof ApiError ? e.message : "אירעה שגיאה, נסו שוב.");
    },
    [pushAssistant],
  );

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      try {
        const business = await api<Business>("/businesses/me");
        if (cancelled) return;
        setBiz(business);
        const history = await api<ChatHistoryResponse>(`/businesses/${business.id}/chat/messages`);
        if (cancelled) return;
        setMessages(history.messages);
        setActiveAction(history.activeAction);
      } catch (e) {
        if (!cancelled) pushError(e);
      } finally {
        if (!cancelled) setHistoryLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user, pushError]);

  const applyTurn = useCallback(
    (res: ChatTurnResult, actionId?: string) => {
      pushAssistant(res.assistantText, {
        actionId: res.action?.id ?? actionId ?? null,
        pdfUrl: res.result?.pdfUrl ?? null,
      });
      setActiveAction(res.action && res.action.status === "pending_confirmation" ? res.action : null);
    },
    [pushAssistant],
  );

  const deliver = useCallback(
    async (localId: string, text: string) => {
      if (!biz) return;
      setSending(true);
      try {
        const res = await api<ChatTurnResult>(`/businesses/${biz.id}/chat/message`, {
          method: "POST",
          body: JSON.stringify({ text }),
        });
        setMessages((prev) => prev.map((m) => (m.id === localId ? { ...m, sendStatus: undefined } : m)));
        applyTurn(res);
      } catch (e) {
        if (e instanceof ApiError) {
          // server rejected the message itself (e.g. 422): show its Hebrew message, no retry
          setMessages((prev) => prev.map((m) => (m.id === localId ? { ...m, sendStatus: undefined } : m)));
          pushError(e);
        } else {
          // network failure: keep the bubble, offer inline retry
          setMessages((prev) =>
            prev.map((m) => (m.id === localId ? { ...m, sendStatus: "failed" as const } : m)),
          );
        }
      } finally {
        setSending(false);
      }
    },
    [biz, applyTurn, pushError],
  );

  const send = useCallback(
    (text: string) => {
      const localId = nextLocalId("u");
      setMessages((prev) => [
        ...prev,
        { id: localId, role: "user", text, createdAt: new Date().toISOString(), sendStatus: "pending" },
      ]);
      void deliver(localId, text);
    },
    [deliver],
  );

  const retry = useCallback(
    (messageId: string) => {
      if (sending) return;
      const failed = messages.find((m) => m.id === messageId);
      if (!failed) return;
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, sendStatus: "pending" as const } : m)),
      );
      void deliver(messageId, failed.text);
    },
    [messages, sending, deliver],
  );

  const confirmAction = useCallback(async () => {
    if (!biz || !activeAction) return;
    const actionId = activeAction.id;
    try {
      const res = await api<ChatTurnResult>(`/businesses/${biz.id}/chat/actions/${actionId}/confirm`, {
        method: "POST",
      });
      applyTurn(res, actionId);
    } catch (e) {
      pushError(e);
      setActiveAction(null);
    }
  }, [biz, activeAction, applyTurn, pushError]);

  const cancelAction = useCallback(async () => {
    if (!biz || !activeAction) return;
    const actionId = activeAction.id;
    try {
      await api<{ status: string }>(`/businesses/${biz.id}/chat/actions/${actionId}/cancel`, {
        method: "POST",
      });
      pushAssistant("הפעולה בוטלה.", { actionId });
      setActiveAction(null);
    } catch (e) {
      pushError(e);
      setActiveAction(null);
    }
  }, [biz, activeAction, pushAssistant, pushError]);

  return (
    <div className="flex h-[calc(100dvh-4rem-env(safe-area-inset-bottom,0px))] flex-col">
      {historyLoading ? (
        <div className="flex flex-1 flex-col gap-3 overflow-hidden px-4 py-4" aria-hidden>
          <div className="me-auto h-12 w-3/5 animate-pulse rounded-2xl border border-border bg-white" />
          <div className="ms-auto h-12 w-1/2 animate-pulse rounded-2xl bg-border" />
          <div className="me-auto h-20 w-2/3 animate-pulse rounded-2xl border border-border bg-white" />
        </div>
      ) : (
        <ChatMessageList
          messages={messages}
          activeAction={activeAction}
          onConfirm={confirmAction}
          onCancel={cancelAction}
          onRetry={retry}
        />
      )}
      <ChatInput onSend={send} disabled={sending || historyLoading || !biz} />
    </div>
  );
}
