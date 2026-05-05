import type { FeatureCollection } from 'geojson'
import type { MonthKey } from './geojson'

export interface AppState {
  activeMonth: MonthKey
  cache: Map<MonthKey, FeatureCollection>
  isLoading: boolean
  error: string | null
}

export interface StoreActions {
  setActiveMonth: (month: MonthKey) => void
  setCache: (key: MonthKey, data: FeatureCollection) => void
  setIsLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}
