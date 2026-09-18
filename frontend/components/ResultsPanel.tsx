"use client";

import { useRef } from "react";
import type { ResultResponse } from "@/lib/api";
import { videoUrl } from "@/lib/api";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

interface ResultsPanelProps {
  result: ResultResponse;
  originalFilename: string;
}

export default function ResultsPanel({ result, originalFilename }: ResultsPanelProps) {
  const originalRef = useRef<HTMLVideoElement>(null);

  const seekOriginal = (time: number) => {
    if (originalRef.current) {
      originalRef.current.currentTime = time;
      originalRef.current.play();
    }
  };

  const { analysis } = result;

  return (
    <div className="w-full space-y-12 sm:space-y-16 py-6 sm:py-8">
      {/* Video players side-by-side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 sm:gap-12">
        {/* Original */}
        <div className="space-y-4">
          <div className="flex items-center justify-between px-2">
            <span className="text-xs font-semibold uppercase tracking-widest text-white/50">
              Original Footage
            </span>
            <span className="text-xs text-white/40 truncate max-w-[240px] font-mono">
              {result.original_filename}
            </span>
          </div>
          <div className="rounded-3xl overflow-hidden bg-black/90 border border-white/15 aspect-video shadow-2xl ring-1 ring-white/5">
            <video
              ref={originalRef}
              src={videoUrl(originalFilename)}
              controls
              className="w-full h-full object-contain"
              preload="metadata"
            />
          </div>
        </div>

        {/* AI Director's Cut */}
        <div className="space-y-4">
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-2.5">
              <div className="w-2.5 h-2.5 rounded-full bg-violet-400 animate-pulse" />
              <span className="text-xs font-bold uppercase tracking-widest text-violet-300">
                AI Director&apos;s Cut
              </span>
            </div>
            <a
              href={videoUrl(result.output_filename)}
              download
              className="inline-flex items-center gap-1.5 text-xs text-violet-300 hover:text-white transition-colors bg-violet-500/10 hover:bg-violet-500/25 px-3 py-1.5 rounded-lg border border-violet-500/30"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span>Download Reel</span>
            </a>
          </div>
          <div className="rounded-3xl overflow-hidden bg-black/90 border border-violet-500/40 aspect-video shadow-2xl shadow-violet-500/15 ring-2 ring-violet-500/20">
            <video
              src={videoUrl(result.output_filename)}
              controls
              autoPlay
              className="w-full h-full object-contain"
              preload="metadata"
            />
          </div>
        </div>
      </div>

      {/* AI Director's Summary Banner */}
      <div className="rounded-3xl bg-gradient-to-br from-violet-950/40 via-purple-950/20 to-neutral-900/60 border border-violet-500/30 p-8 sm:p-12 shadow-xl shadow-violet-950/30 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-violet-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-violet-500/15 border border-violet-500/30 text-violet-300 text-xs font-semibold uppercase tracking-wider mb-4">
            <span>AI Director Highlights</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white mb-4 tracking-tight">
            {analysis.title}
          </h2>
          <p className="text-white/70 text-base sm:text-lg leading-relaxed max-w-4xl">
            {analysis.summary}
          </p>
        </div>
      </div>

      {/* Selected Moments Section */}
      <div className="space-y-6 sm:space-y-8 mt-12 sm:mt-16">
        <div className="flex flex-wrap items-center justify-between gap-4 px-2 pb-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <h3 className="text-sm sm:text-base font-bold uppercase tracking-widest text-white/70">
              Selected Moments
            </h3>
            <span className="px-2.5 py-0.5 rounded-full bg-violet-500/20 border border-violet-500/30 text-violet-300 text-xs font-mono font-medium">
              {analysis.clips.length} moments
            </span>
          </div>
          <span className="text-xs text-white/40 font-medium">
            Click any timestamp to seek original video
          </span>
        </div>

        <div className="space-y-6 sm:space-y-7">
          {analysis.clips.map((clip, i) => (
            <div
              key={i}
              className="rounded-3xl bg-[#141224]/80 hover:bg-[#1A1730] border border-white/12 hover:border-violet-500/40 p-6 sm:p-8 transition-all duration-300 shadow-lg hover:shadow-violet-900/20 group"
            >
              <div className="flex items-start gap-5 sm:gap-7">
                {/* Moment Number Badge */}
                <div className="flex-shrink-0 w-11 h-11 rounded-2xl bg-gradient-to-br from-violet-600/30 to-fuchsia-600/20 border border-violet-400/30 flex items-center justify-center text-base font-bold text-violet-300 shadow-inner group-hover:scale-105 transition-transform">
                  {i + 1}
                </div>

                {/* Moment Details */}
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-3.5 mb-4">
                    {/* Timestamp Button */}
                    <button
                      id={`seek-clip-${i}`}
                      onClick={() => seekOriginal(clip.start)}
                      className="font-mono text-sm text-violet-200 hover:text-white bg-violet-500/15 hover:bg-violet-500/30 px-4 py-2 rounded-xl transition-all border border-violet-400/30 cursor-pointer shadow-sm flex items-center gap-2 group-hover:border-violet-400/50"
                      title="Click to seek original video"
                    >
                      <svg className="w-3.5 h-3.5 text-violet-400" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z" />
                      </svg>
                      <span>{formatTime(clip.start)} – {formatTime(clip.end)}</span>
                    </button>

                    {/* Score Bar */}
                    <div className="flex items-center gap-1.5 px-3 py-2 bg-black/40 rounded-xl border border-white/10">
                      <div className="flex items-center gap-1">
                        {Array.from({ length: 10 }).map((_, j) => (
                          <div
                            key={j}
                            className={`w-1.5 h-3.5 rounded-sm ${
                              j < clip.score ? "bg-violet-400" : "bg-white/10"
                            }`}
                          />
                        ))}
                      </div>
                      <span className="text-xs text-white/50 ml-2 font-mono font-medium">{clip.score}/10</span>
                    </div>

                    {/* Overlay Title Pill */}
                    {clip.overlay_title && (
                      <span className="text-xs font-semibold text-white/90 bg-white/[0.08] px-3 py-1.5 rounded-xl border border-white/15 shadow-sm">
                        {clip.overlay_title}
                      </span>
                    )}
                  </div>

                  {/* Reason Text */}
                  <p className="text-white/75 text-sm sm:text-base leading-relaxed pl-0.5">
                    {clip.reason}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* AI Narration Side-by-Side Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 sm:gap-10 mt-14 sm:mt-18">
        {/* Opening Narration */}
        <div className="rounded-3xl bg-[#13111C]/80 border border-white/12 p-8 sm:p-10 space-y-5 shadow-xl hover:border-emerald-500/30 transition-colors">
          <div className="flex items-center gap-2.5">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
            <span className="text-xs font-bold uppercase tracking-widest text-emerald-400/90">
              Opening Narration
            </span>
          </div>
          <p className="text-white/85 text-base sm:text-lg italic leading-relaxed pt-2 pl-3 border-l-2 border-emerald-500/40">
            &ldquo;{analysis.intro}&rdquo;
          </p>
        </div>

        {/* Closing Narration */}
        <div className="rounded-3xl bg-[#13111C]/80 border border-white/12 p-8 sm:p-10 space-y-5 shadow-xl hover:border-rose-500/30 transition-colors">
          <div className="flex items-center gap-2.5">
            <div className="w-2.5 h-2.5 rounded-full bg-rose-400" />
            <span className="text-xs font-bold uppercase tracking-widest text-rose-400/90">
              Closing Narration
            </span>
          </div>
          <p className="text-white/85 text-base sm:text-lg italic leading-relaxed pt-2 pl-3 border-l-2 border-rose-500/40">
            &ldquo;{analysis.outro}&rdquo;
          </p>
        </div>
      </div>

      {/* Director's Notes */}
      {analysis.editing_notes?.length > 0 && (
        <div className="rounded-3xl bg-[#13111C]/80 border border-white/12 p-8 sm:p-12 space-y-6 shadow-xl mt-12 sm:mt-16 mb-8">
          <div className="flex items-center gap-3 pb-3 border-b border-white/10">
            <span className="text-violet-400">✦</span>
            <h4 className="text-xs sm:text-sm font-bold uppercase tracking-widest text-white/60">
              Director&apos;s Notes
            </h4>
          </div>
          <ul className="space-y-4 pt-2">
            {analysis.editing_notes.map((note, i) => (
              <li
                key={i}
                className="flex items-start gap-4 text-sm sm:text-base text-white/70 leading-relaxed p-4 rounded-2xl bg-white/[0.02] border border-white/5"
              >
                <span className="text-violet-400 mt-1 flex-shrink-0 text-xs">◆</span>
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
