/**
 * A–F regulatory scale for PM2.5 (µg/m³).
 * Source of truth — fixed by PRD §Feature 1, mirrored in CONTRACTS.md §4.
 * Do not edit values here without updating the contract.
 */

import type { Grade, GradeBin } from "@/types/lsoa";

export const WHO_PM25 = 5;   // µg/m³  WHO 2021 guideline
export const UK_2040 = 10;   // µg/m³  UK 2040 target

export const GRADE_BINS: readonly GradeBin[] = [
  { grade: "A", min: 0,  max: 5,        color: "#00c864", label: "Meets WHO 2021" },
  { grade: "B", min: 5,  max: 10,       color: "#c8e632", label: "Meets UK 2040" },
  { grade: "C", min: 10, max: 15,       color: "#ffc800", label: "Above UK 2040" },
  { grade: "D", min: 15, max: 20,       color: "#ff8200", label: "Concerning" },
  { grade: "E", min: 20, max: 25,       color: "#e63232", label: "Critical" },
  { grade: "F", min: 25, max: Infinity, color: "#960096", label: "Urgent action" },
] as const;

export function gradeOf(pm25: number): Grade {
  if (pm25 < 5) return "A";
  if (pm25 < 10) return "B";
  if (pm25 < 15) return "C";
  if (pm25 < 20) return "D";
  if (pm25 < 25) return "E";
  return "F";
}

export function colorFor(pm25: number): string {
  return GRADE_BINS.find((b) => pm25 >= b.min && pm25 < b.max)?.color ?? "#960096";
}
