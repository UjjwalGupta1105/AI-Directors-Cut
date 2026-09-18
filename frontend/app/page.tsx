"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import UploadSection from "@/components/UploadSection";
import ProcessingPipeline from "@/components/ProcessingPipeline";
import ResultsPanel from "@/components/ResultsPanel";
import { getStatus, getResult, type ResultResponse, type StatusResponse } from "@/lib/api";

type AppState = "idle" | "processing" | "completed" | "failed";

export default function Home() {
  const [appState, setAppState] = useState<AppState>("idle");
  const [jobId, setJobId] = useState<string>("");
  const [originalFilename, setOriginalFilename] = useState<string>("");
  const [status, setStatus] = useState<StatusResponse>({
    status: "uploaded",
    progress: 0,
    message: "Starting...",
  });
  const [result, setResult] = useState<ResultResponse | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const poll = useCallback(async (id: string) => {
    try {
      const s = await getStatus(id);
      setStatus(s);

      if (s.status === "completed") {
        stopPolling();
        const r = await getResult(id);
        setResult(r);
        setAppState("completed");
      } else if (s.status === "failed") {
        stopPolling();
        setAppState("failed");
      }
    } catch (e: unknown) {
      console.error("Poll error:", e);
      // If server restarted or job not found, show failed state
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("404") || msg.includes("not found") || msg.includes("fetch")) {
        stopPolling();
        setStatus(prev => ({
          ...prev,
          status: "failed",
          error: "Connection lost or server was restarted. Please click 'Start over' and try again.",
        }));
        setAppState("failed");
      }
    }
  }, []);

  const handleUploadComplete = useCallback(
    (id: string, file: File) => {
      setJobId(id);
      setOriginalFilename(`${id}_${file.name.replace(/\s+/g, "_")}`);
      setAppState("processing");
      setStatus({ status: "uploaded", progress: 5, message: "Processing started..." });

      pollRef.current = setInterval(() => poll(id), 2500);
    },
    [poll]
  );

  useEffect(() => {
    return () => stopPolling();
  }, []);

  const handleReset = () => {
    stopPolling();
    setAppState("idle");
    setJobId("");
    setResult(null);
    setStatus({ status: "uploaded", progress: 0, message: "Starting..." });
  };

  return (
    <main className="h-screen bg-[#080810] text-white w-full relative overflow-y-auto overflow-x-hidden flex flex-col justify-between">
      {/* Ambient background glows */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-violet-600/8 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-fuchsia-600/6 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-indigo-600/4 rounded-full blur-3xl" />
      </div>

      {/* Main Container — 90% width, vertically centered with generous padding */}
      <div className="relative z-10 w-[90%] max-w-7xl self-center py-12 sm:py-16 flex flex-col items-center justify-center flex-1 my-auto pb-28 sm:pb-36">
        {/* Header */}
        <header className="text-center mb-10 sm:mb-14 w-full">
          <h1 className="text-5xl sm:text-6xl font-bold mb-5 tracking-tight flex items-center justify-center gap-3 sm:gap-4 flex-wrap">
            <span className="bg-gradient-to-r from-white via-white/90 to-white/60 bg-clip-text text-transparent">
              AI Director&apos;s
            </span>
            <span className="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
              Cut
            </span>
          </h1>

          <p className="text-base sm:text-lg text-white/40 mx-auto leading-relaxed">
            Turn raw footage into a cinematic highlight reel.
          </p>

          {(appState === "completed" || appState === "failed") && (
            <div className="mt-8 flex justify-center">
              <button
                onClick={handleReset}
                className="inline-flex items-center gap-2 text-sm text-white/60 hover:text-white transition-all border border-white/12 rounded-full px-6 py-3 hover:border-white/30 hover:bg-white/5 cursor-pointer shadow-sm"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>Start over</span>
              </button>
            </div>
          )}
        </header>

        {/* Content Area */}
        <div className="w-full flex flex-col items-center gap-10">
          {appState === "idle" && (
            <div className="w-full flex justify-center py-4">
              <UploadSection onUploadComplete={handleUploadComplete} />
            </div>
          )}

          {appState === "processing" && (
            <div className="w-full flex justify-center py-4">
              <ProcessingPipeline
                status={status.status}
                progress={status.progress}
                message={status.message}
                error={status.error}
              />
            </div>
          )}

          {appState === "failed" && (
            <div className="w-full flex justify-center py-4">
              <ProcessingPipeline
                status="failed"
                progress={status.progress}
                message={status.message}
                error={status.error}
              />
            </div>
          )}

          {appState === "completed" && result && (
            <div className="w-full py-6 sm:py-10">
              <ResultsPanel
                result={result}
                originalFilename={originalFilename}
              />
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="relative z-10 py-6 border-t border-white/5 text-center text-xs text-white/20">
        AI Director&apos;s Cut · Google Gemini · FFmpeg · Local processing
      </footer>
    </main>
  );
}
