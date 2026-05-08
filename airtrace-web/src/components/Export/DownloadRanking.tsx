import Papa from "papaparse";
import { saveAs } from "file-saver";
import type { LoadedData } from "@/types/lsoa";
import { useAppStore } from "@/store/useAppStore";
import { buildRanking } from "@/lib/exposure";

interface Props { data: LoadedData; }

export function DownloadRanking({ data }: Props) {
  const fromYM = useAppStore((s) => s.fromYM);
  const toYM = useAppStore((s) => s.toYM);
  const greenCoverMax = useAppStore((s) => s.greenCoverMax);
  const popDensityMin = useAppStore((s) => s.popDensityMin);

  const handleDownload = () => {
    const ranking = buildRanking(
      data.lsoaGeo.features, data.series, fromYM, toYM,
      { greenCoverMax, popDensityMin },
    );
    const csv = Papa.unparse(ranking, {
      columns: [
        "rank", "LSOA21CD", "LSOA21NM",
        "mean_pm25", "n_months",
        "ratio_vs_who", "ratio_vs_uk2040",
        "score",
        "pct_green", "pop_density_km2", "population",
      ],
    });
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const filename = `airtrace_ranking_${fromYM}_${toYM}.csv`;
    saveAs(blob, filename);
  };

  return (
    <section className="mb-4">
      <button
        onClick={handleDownload}
        className="w-full px-3 py-2 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition-colors"
      >
        Download ranking (CSV)
      </button>
      <p className="text-[10px] text-slate-500 mt-1">
        Window {fromYM} → {toYM}. Filters apply. Sorted by mean PM2.5 descending.
      </p>
    </section>
  );
}
