import { useEffect, useRef, useState } from "react";
import { useAppStore } from "@/store/useAppStore";

interface Props { months: string[]; }

const ADVANCE_MS = 380;          // one month every 380ms → ~23s for 60 months
const COMMIT_DEBOUNCE_MS = 120;

/**
 * Dual-handle slider over months[]. Includes a play/pause button that auto-
 * advances the right handle (toYM) one month per tick; reaching the end stops.
 * Any manual drag pauses playback.
 */
export function DateRangeSlider({ months }: Props) {
  const fromYM = useAppStore((s) => s.fromYM);
  const toYM = useAppStore((s) => s.toYM);
  const playing = useAppStore((s) => s.playing);
  const setRange = useAppStore((s) => s.setRange);
  const togglePlay = useAppStore((s) => s.togglePlay);
  const setPlaying = useAppStore((s) => s.setPlaying);

  const last = months.length - 1;
  const fromIdx = Math.max(0, months.indexOf(fromYM));
  const toIdx = months.indexOf(toYM) === -1 ? last : months.indexOf(toYM);

  const [localFrom, setLocalFrom] = useState(fromIdx);
  const [localTo, setLocalTo] = useState(toIdx);

  // External store changes (reset etc.) sync into local state.
  useEffect(() => { setLocalFrom(fromIdx); }, [fromIdx]);
  useEffect(() => { setLocalTo(toIdx); }, [toIdx]);

  // Debounced commit to store on local change.
  useEffect(() => {
    const handle = setTimeout(() => {
      const f = months[Math.min(localFrom, localTo)];
      const t = months[Math.max(localFrom, localTo)];
      if (f !== fromYM || t !== toYM) setRange(f, t);
    }, COMMIT_DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [localFrom, localTo, months, fromYM, toYM, setRange]);

  // Auto-advance while playing.
  const timerRef = useRef<number | null>(null);
  useEffect(() => {
    if (!playing) return;
    timerRef.current = window.setInterval(() => {
      setLocalTo((prev) => {
        if (prev >= last) {
          // Reached the end — stop playback.
          setPlaying(false);
          return last;
        }
        return prev + 1;
      });
    }, ADVANCE_MS);
    return () => {
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [playing, last, setPlaying]);

  const onUserDragFrom = (v: number) => {
    if (playing) setPlaying(false);
    setLocalFrom(v);
  };
  const onUserDragTo = (v: number) => {
    if (playing) setPlaying(false);
    setLocalTo(v);
  };

  const onPlayClick = () => {
    // If at the end already, restart from the from-handle.
    if (localTo >= last) setLocalTo(Math.min(localFrom + 1, last));
    togglePlay();
  };

  const fLabel = months[Math.min(localFrom, localTo)];
  const tLabel = months[Math.max(localFrom, localTo)];

  return (
    <div className="absolute bottom-6 left-3 z-10 w-[460px] bg-slate-950/85 backdrop-blur-md border border-white/10 rounded-xl p-4 shadow-xl text-xs text-slate-200">
      <div className="flex items-center gap-3 mb-3">
        <button
          onClick={onPlayClick}
          className="flex-shrink-0 w-9 h-9 rounded-full bg-emerald-500 hover:bg-emerald-400 text-white flex items-center justify-center transition-all duration-150 shadow-lg shadow-emerald-500/30 hover:shadow-emerald-400/40"
          aria-label={playing ? "Pause" : "Play"}
          title={playing ? "Pause animation" : "Animate window forward"}
        >
          {playing ? (
            <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
              <rect x="2" y="1" width="3.5" height="12" rx="0.6" />
              <rect x="8.5" y="1" width="3.5" height="12" rx="0.6" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
              <path d="M3 1.5 L12 7 L3 12.5 Z" />
            </svg>
          )}
        </button>
        <div className="flex-1">
          <div className="flex justify-between items-baseline">
            <span className="text-[11px] uppercase tracking-wider text-slate-400">Window</span>
            <span className="font-mono text-white">{fLabel} → {tLabel}</span>
          </div>
        </div>
      </div>

      <div className="relative h-6">
        <div className="absolute top-2.5 left-0 right-0 h-1 bg-white/10 rounded-full" />
        <div
          className={`absolute top-2.5 h-1 rounded ${playing ? "bg-emerald-300" : "bg-emerald-400"}`}
          style={{
            left: `${(Math.min(localFrom, localTo) / last) * 100}%`,
            right: `${100 - (Math.max(localFrom, localTo) / last) * 100}%`,
            transition: playing ? 'left 360ms ease-out, right 360ms ease-out' : 'none',
          }}
        />
        <input
          type="range" min={0} max={last} value={localFrom}
          onChange={(e) => onUserDragFrom(Number(e.target.value))}
          className="absolute inset-0 w-full h-6 appearance-none bg-transparent pointer-events-auto cursor-pointer slider-thumb"
          aria-label="From month"
        />
        <input
          type="range" min={0} max={last} value={localTo}
          onChange={(e) => onUserDragTo(Number(e.target.value))}
          className="absolute inset-0 w-full h-6 appearance-none bg-transparent pointer-events-auto cursor-pointer slider-thumb"
          aria-label="To month"
        />
      </div>
    </div>
  );
}
