import { create } from "zustand";
import type { AppState } from "@/types/lsoa";

const DEFAULT_FROM = "2021-01";
const DEFAULT_TO = "2025-12";

export const useAppStore = create<AppState>((set) => ({
  viewMode: "streets",
  pollutant: "PM2.5",
  fromYM: DEFAULT_FROM,
  toYM: DEFAULT_TO,
  selectedLsoa: null,
  showOverlay: true,
  popDensityMin: null,
  playing: false,
  showSidebar: true,

  setViewMode: (m) => set({ viewMode: m }),
  setPollutant: (p) => set({ pollutant: p }),
  setRange: (from, to) => set({ fromYM: from, toYM: to }),
  setSelected: (id) => set({ selectedLsoa: id }),
  toggleOverlay: () => set((s) => ({ showOverlay: !s.showOverlay })),
  setPopDensityMin: (v) => set({ popDensityMin: v }),
  setPlaying: (v) => set({ playing: v }),
  togglePlay: () => set((s) => ({ playing: !s.playing })),
  toggleSidebar: () => set((s) => ({ showSidebar: !s.showSidebar })),
}));
