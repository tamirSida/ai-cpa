import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "AI Bookkeeper",
    short_name: "Bookkeeper",
    description: "הנהלת חשבונות בצ'אט לעוסק פטור",
    start_url: "/chat",
    display: "standalone",
    dir: "rtl",
    lang: "he",
    background_color: "#f1f5fd",
    theme_color: "#2563eb",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
