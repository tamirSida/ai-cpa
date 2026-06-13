"use client";
import { useBusiness } from "@/lib/business";

export default function DashboardPage() {
  const { business, loading } = useBusiness();
  return (
    <div className="p-4">
      {loading ? (
        <div className="h-8 w-48 animate-pulse rounded-xl bg-border" aria-hidden />
      ) : (
        <>
          <h1 className="text-2xl font-semibold">שלום, {business?.businessName}</h1>
          <p className="mt-1 text-sm text-foreground/60">הסקירה המלאה תתווסף בשלב 5.</p>
        </>
      )}
    </div>
  );
}
