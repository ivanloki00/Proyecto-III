import { create } from 'zustand'
import type { FeatureCollection } from 'geojson'
import type { MonthKey } from '../types/geojson'
import type { AppState, StoreActions } from '../types/store'

const useAppStore = create<AppState & StoreActions>()((set) => ({
  activeMonth: 'annual',
  setActiveMonth: (month) => set({ activeMonth: month }),

  cache: new Map<MonthKey, FeatureCollection>(),
  setCache: (key, data) =>
    set((state) => ({ cache: new Map(state.cache).set(key, data) })),

  isLoading: true,
  setIsLoading: (loading) => set({ isLoading: loading }),

  error: null,
  setError: (error) => set({ error }),
}))

export default useAppStore
