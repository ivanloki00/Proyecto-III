import type { Feature, Geometry } from 'geojson'

export type MonthKey =
  | 'annual'
  | '2024-01'
  | '2024-02'
  | '2024-03'
  | '2024-04'
  | '2024-05'
  | '2024-06'
  | '2024-07'
  | '2024-08'
  | '2024-09'
  | '2024-10'
  | '2024-11'
  | '2024-12'

export interface FeatureProps {
  name: string | null
  road_type: string
  score: string
  pm25_annual: number
  pm10_annual: number
}

export interface PollutionFeature extends Feature<Geometry, FeatureProps> {}
