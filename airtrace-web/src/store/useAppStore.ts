import { create } from "zustand";
import type { AppState } from "@/types/lsoa";

const DEFAULT_FROM = "2021-01";
const DEFAULT_TO = "2025-12";

export const useAppStore = create<AppState>((set) => ({
  viewMode: "streets",
  fromYM: DEFAULT_FROM,
  toYM: DEFAULT_TO,
  selectedLsoa: null,
  showOverlay: true,
  greenCoverMax: null,
  popDensityMin: null,
  playing: false,

  setViewMode: (m) => set({ viewMode: m }),
  setRange: (from, to) => set({ fromYM: from, toYM: to }),
  setSelected: (id) => set({ selectedLsoa: id }),
  toggleOverlay: () => set((s) => ({ showOverlay: !s.showOverlay })),
  setGreenCoverMax: (v) => set({ greenCoverMax: v }),
  setPopDensityMin: (v) => set({ popDensityMin: v }),
  setPlaying: (v) => set({ playing: v }),
  togglePlay: () => set((s) => ({ playing: !s.playing })),
}));
