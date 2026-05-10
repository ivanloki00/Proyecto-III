/**
 * A–F regulatory scale for PM2.5 (µg/m³).
 * Source of truth — fixed by PRD §Feature 1, mirrored in CONTRACTS.md §4.
 * Do not edit values here without updating the contract.
 */

import type { Grade, GradeBin, Pollutant } from "@/types/lsoa";

export const WHO_PM25 = 5;    // µg/m³  WHO 2021 annual guideline
export const UK_2040  = 10;   // µg/m³  UK 2040 target
export const WHO_PM10 = 15;   // µg/m³  WHO 2021 annual guideline
export const UK_PM10  = 40;   // µg/m³  UK LAQM annual objective

export const GRADE_BINS: readonly GradeBin[] = [
  { grade: "A", min: 0,  max: 5,        color: "#00c864", label: "Meets WHO 2021" },
  { grade: "B", min: 5,  max: 10,       color: "#c8e632", label: "Meets UK 2040" },
  { grade: "C", min: 10, max: 15,       color: "#ffc800", label: "Above UK 2040" },
  { grade: "D", min: 15, max: 20,       color: "#ff8200", label: "Concerning" },
  { grade: "E", min: 20, max: 25,       color: "#e63232", label: "Critical" },
  { grade: "F", min: 25, max: Infinity, color: "#960096", label: "Urgent action" },
] as const;

export const GRADE_BINS_PM10: readonly GradeBin[] = [
  { grade: "A", min: 0,  max: 15,       color: "#00c864", label: "Meets WHO 2021" },
  { grade: "B", min: 15, max: 30,       color: "#c8e632", label: "Good" },
  { grade: "C", min: 30, max: 45,       color: "#ffc800", label: "Above WHO daily" },
  { grade: "D", min: 45, max: 60,       color: "#ff8200", label: "Concerning" },
  { grade: "E", min: 60, max: 75,       color: "#e63232", label: "Critical" },
  { grade: "F", min: 75, max: Infinity, color: "#960096", label: "Urgent action" },
] as const;

export function gradeOf(pm25: number): Grade {
  if (pm25 < 5) return "A";
  if (pm25 < 10) return "B";
  if (pm25 < 15) return "C";
  if (pm25 < 20) return "D";
  if (pm25 < 25) return "E";
  return "F";
}

export function gradeOfPM10(pm10: number): Grade {
  if (pm10 < 15) return "A";
  if (pm10 < 30) return "B";
  if (pm10 < 45) return "C";
  if (pm10 < 60) return "D";
  if (pm10 < 75) return "E";
  return "F";
}

export function gradeForPollutant(value: number, pollutant: Pollutant): Grade {
  return pollutant === "PM10" ? gradeOfPM10(value) : gradeOf(value);
}

export function binsForPollutant(pollutant: Pollutant): readonly GradeBin[] {
  return pollutant === "PM10" ? GRADE_BINS_PM10 : GRADE_BINS;
}

export function colorFor(pm25: number): string {
  return GRADE_BINS.find((b) => pm25 >= b.min && pm25 < b.max)?.color ?? "#960096";
}
