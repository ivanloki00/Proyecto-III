import Papa from "papaparse";
import { saveAs } from "file-saver";
import type { LoadedData } from "@/types/lsoa";
import { useAppStore } from "@/store/useAppStore";
import { buildRanking } from "@/lib/exposure";

interface Props { data: LoadedData; }

export function DownloadRanking({ data }: Props) {
  const fromYM = useAppStore((s) => s.fromYM);
  const toYM = useAppStore((s) => s.toYM);
  const popDensityMin = useAppStore((s) => s.popDensityMin);

  const handleDownload = () => {
    const ranking = buildRanking(
      data.lsoaGeo.features, data.series, fromYM, toYM,
      { popDensityMin },
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
        style={{
          width: '100%', padding: '8px 14px',
          background: '#10B981', color: '#fff',
          border: 0, borderRadius: 6,
          font: '600 12px Inter, system-ui, sans-serif',
          cursor: 'pointer',
          boxShadow: '0 8px 24px rgba(16,185,129,0.30)',
          transition: 'background 150ms, box-shadow 150ms',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = '#34D399';
          e.currentTarget.style.boxShadow = '0 8px 28px rgba(16,185,129,0.45)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = '#10B981';
          e.currentTarget.style.boxShadow = '0 8px 24px rgba(16,185,129,0.30)';
        }}
      >
        Download ranking CSV
      </button>
      <p className="text-[10px] text-slate-500 mt-1.5 font-mono">
        {fromYM} → {toYM} · filters apply · sorted by concentration desc.
      </p>
    </section>
  );
}
