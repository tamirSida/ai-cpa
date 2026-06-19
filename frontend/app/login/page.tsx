"use client";

import {
  GoogleAuthProvider,
  signInWithEmailAndPassword,
  signInWithPopup,
} from "firebase/auth";
import { Loader2, LogIn, Mail } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { auth } from "@/lib/firebase";

// Public, $5-capped demo account — the one-click button below signs in with it so people
// you show the app to don't need credentials.
const DEMO_EMAIL = "demo@portfolio-plus.com";
const DEMO_PASSWORD = "DemoTax2026!";

const inputClass =
  "min-h-12 w-full rounded-xl border border-border bg-white px-4 text-base focus:outline-none focus:ring-2 focus:ring-primary";

export default function LoginPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    if (!loading && user) router.replace("/chat");
  }, [user, loading, router]);

  async function run(fn: () => Promise<unknown>) {
    setError(null);
    setPending(true);
    try {
      await fn();
      router.replace("/chat");
    } catch {
      setError("ההתחברות נכשלה — בדוק את הפרטים ונסה שוב");
      setPending(false);
    }
  }

  const signInGoogle = () => run(() => signInWithPopup(auth, new GoogleAuthProvider()));
  const signInDemo = () => run(() => signInWithEmailAndPassword(auth, DEMO_EMAIL, DEMO_PASSWORD));
  function signInEmail() {
    if (!email.trim() || !password) {
      setError("יש להזין אימייל וסיסמה");
      return;
    }
    run(() => signInWithEmailAndPassword(auth, email.trim(), password));
  }

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-white p-6">
        <h1 className="text-center text-2xl font-semibold">AI Bookkeeper</h1>
        <p className="mt-2 text-center text-sm text-foreground/60">
          {"הנהלת חשבונות בצ'אט לעוסק פטור — קבלות, הוצאות ודוח שנתי"}
        </p>

        <button
          onClick={signInGoogle}
          disabled={pending}
          className="mt-6 flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          {pending ? <Loader2 size={20} className="animate-spin" aria-hidden /> : <LogIn size={20} aria-hidden />}
          התחברות עם Google
        </button>

        <div className="my-4 flex items-center gap-3 text-xs text-foreground/40">
          <span className="h-px flex-1 bg-border" />
          או
          <span className="h-px flex-1 bg-border" />
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            signInEmail();
          }}
          className="flex flex-col gap-3"
        >
          <input
            type="email"
            dir="ltr"
            inputMode="email"
            autoComplete="email"
            placeholder="name@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputClass}
            aria-label="אימייל"
          />
          <input
            type="password"
            dir="ltr"
            autoComplete="current-password"
            placeholder="סיסמה"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputClass}
            aria-label="סיסמה"
          />
          <button
            type="submit"
            disabled={pending}
            className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-primary px-5 font-medium text-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
          >
            <Mail size={18} aria-hidden />
            התחברות עם אימייל
          </button>
        </form>

        <button
          onClick={signInDemo}
          disabled={pending}
          className="mt-3 min-h-12 w-full rounded-xl bg-muted px-5 text-sm font-medium text-foreground/70 transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          כניסה לחשבון דמו
        </button>

        {error && <p className="mt-3 text-center text-sm text-destructive">{error}</p>}
      </div>
    </main>
  );
}
