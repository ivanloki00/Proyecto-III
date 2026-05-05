import type { FeatureCollection } from 'geojson'
import type { MonthKey, FeatureProps } from './geojson'

export interface AppState {
  activeMonth: MonthKey
  cache: Map<MonthKey, FeatureCollection>
  isLoading: boolean
  error: string | null
  activeSegment: FeatureProps | null
  infoCardCorner: 'bottom-left' | 'bottom-right'
}

export interface StoreActions {
  setActiveMonth: (month: MonthKey) => void
  setCache: (key: MonthKey, data: FeatureCollection) => void
  setIsLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setActiveSegment: (f: FeatureProps | null) => void
  setInfoCardCorner: (c: 'bottom-left' | 'bottom-right') => void
}
