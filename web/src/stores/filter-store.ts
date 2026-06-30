"use client";
import { create } from "zustand";

interface ScannerFilters {
  sector?: string;
  minScore?: number;
  limit: number;
  offset: number;
  sort: "composite_score" | "symbol";
}

interface FilterStore {
  scannerFilters: ScannerFilters;
  setScannerFilters: (f: Partial<ScannerFilters>) => void;
  resetScannerFilters: () => void;
}

const DEFAULT_SCANNER_FILTERS: ScannerFilters = {
  sector: undefined,
  minScore: undefined,
  limit: 50,
  offset: 0,
  sort: "composite_score",
};

export const useFilterStore = create<FilterStore>()((set) => ({
  scannerFilters: DEFAULT_SCANNER_FILTERS,
  setScannerFilters: (f) =>
    set((s) => ({ scannerFilters: { ...s.scannerFilters, ...f, offset: 0 } })),
  resetScannerFilters: () => set({ scannerFilters: DEFAULT_SCANNER_FILTERS }),
}));
