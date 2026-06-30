"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UiStore {
  commandPaletteOpen: boolean;
  sidebarCollapsed: boolean;
  tableDensity: "comfortable" | "compact";
  reduceMotionOverride: boolean;
  setCommandPaletteOpen: (v: boolean) => void;
  toggleCommandPalette: () => void;
  setSidebarCollapsed: (v: boolean) => void;
  setTableDensity: (v: "comfortable" | "compact") => void;
  setReduceMotionOverride: (v: boolean) => void;
}

export const useUiStore = create<UiStore>()(
  persist(
    (set, get) => ({
      commandPaletteOpen: false,
      sidebarCollapsed: false,
      tableDensity: "comfortable",
      reduceMotionOverride: false,
      setCommandPaletteOpen: (v) => set({ commandPaletteOpen: v }),
      toggleCommandPalette: () => set({ commandPaletteOpen: !get().commandPaletteOpen }),
      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
      setTableDensity: (v) => set({ tableDensity: v }),
      setReduceMotionOverride: (v) => set({ reduceMotionOverride: v }),
    }),
    { name: "saakshya-ui", partialize: (s) => ({ tableDensity: s.tableDensity, sidebarCollapsed: s.sidebarCollapsed }) }
  )
);
