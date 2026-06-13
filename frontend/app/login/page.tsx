"use client";

import { GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import { Loader2, LogIn } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { auth } from "@/lib/firebase";

export default function LoginPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/chat");
  }, [user, loading, router]);

  async function signIn() {
    setError(null);
    setPending(true);
    try {
      await signInWithPopup(auth, new GoogleAuthProvider());
      router.replace("/chat");
    } catch {
      setError("ההתחברות נכשלה, נסה שוב");
      setPending(false);
    }
  }

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-white p-6 text-center">
        <h1 className="text-2xl font-semibold">AI Bookkeeper</h1>
        <p className="mt-2 text-sm text-foreground/60">
          {"הנהלת חשבונות בצ'אט לעוסק פטור — קבלות, הוצאות ודוח שנתי"}
        </p>
        <button
          onClick={signIn}
          disabled={pending}
          className="mt-6 flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          {pending ? (
            <Loader2 size={20} className="animate-spin" aria-hidden />
          ) : (
            <LogIn size={20} aria-hidden />
          )}
          התחברות עם Google
        </button>
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </div>
    </main>
  );
}
