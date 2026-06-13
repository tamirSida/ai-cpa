"use client";

import { useEffect } from "react";

export function useIosKeyboardFix() {
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    let lastTop = vv.offsetTop;
    const onResize = () => {
      if (vv.offsetTop < lastTop && vv.offsetTop !== 0) {
        window.scrollBy(0, -1);
        window.scrollBy(0, 1);
      }
      lastTop = vv.offsetTop;
    };
    vv.addEventListener("resize", onResize);
    return () => vv.removeEventListener("resize", onResize);
  }, []);
}
