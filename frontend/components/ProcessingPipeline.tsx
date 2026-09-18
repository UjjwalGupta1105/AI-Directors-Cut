"use client";

interface Stage {
  id: string;
  label: string;
  message: string;
  icon: React.ReactNode;
}

const STAGES: Stage[] = [
  {
    id: "uploaded",
    label: "Upload",
    message: "Uploading your video...",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
        />
      </svg>
    ),
  },
  {
    id: "analyzing",
    label: "Analyze",
    message: "Analyzing video with Gemini...",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
        />
      </svg>
    ),
  },
  {
    id: "selecting",
    label: "AI Director",
    message: "Finding the best moments...",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z"
        />
      </svg>
    ),
  },
  {
    id: "generating_audio",
    label: "Narration",
    message: "Generating AI narration...",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 016 0v6a3 3 0 01-3 3z"
        />
      </svg>
    ),
  },
  {
    id: "rendering",
    label: "Render",
    message: "Rendering final video...",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"
        />
      </svg>
    ),
  },
  {
    id: "completed",
    label: "Complete",
    message: "Your highlight reel is ready!",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ),
  },
];

const STATUS_ORDER = ["uploaded", "analyzing", "selecting", "generating_audio", "rendering", "completed"];

interface ProcessingPipelineProps {
  status: string;
  progress: number;
  message: string;
  error?: string;
}

export default function ProcessingPipeline({ status, progress, message, error }: ProcessingPipelineProps) {
  const currentIdx = STATUS_ORDER.indexOf(status);

  return (
    <div className="w-full max-w-2xl mx-auto my-4 sm:my-6 space-y-10">
      {/* Stage pipeline */}
      <div className="flex items-center justify-between mb-10 relative px-3">
        <div className="absolute top-5 left-4 right-4 h-0.5 bg-white/10 z-0" />
        <div
          className="absolute top-5 left-4 h-0.5 bg-gradient-to-r from-violet-500 to-fuchsia-500 z-0 transition-all duration-700"
          style={{ width: `${Math.max(0, (currentIdx / (STAGES.length - 1)) * 95)}%` }}
        />

        {STAGES.map((stage, idx) => {
          const isDone = idx < currentIdx;
          const isCurrent = idx === currentIdx;

          return (
            <div key={stage.id} className="flex flex-col items-center gap-3 z-10">
              <div
                className={`
                w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-500
                ${isDone
                  ? "bg-gradient-to-br from-violet-600 to-fuchsia-600 border-transparent text-white shadow-md shadow-violet-500/20"
                  : isCurrent
                  ? "bg-violet-600/20 border-violet-400 text-violet-300 animate-pulse ring-4 ring-violet-500/10"
                  : "bg-neutral-900 border-white/10 text-white/20"
                }
              `}
              >
                {isDone ? (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  stage.icon
                )}
              </div>
              <span
                className={`text-xs font-medium transition-colors ${
                  isCurrent ? "text-violet-300 font-semibold" : isDone ? "text-white/70" : "text-white/20"
                }`}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Status card */}
      {error ? (
        <div className="rounded-2xl bg-red-500/10 border border-red-500/20 p-10 text-center">
          <div className="w-14 h-14 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-5">
            <svg className="w-7 h-7 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <p className="text-red-300 font-semibold mb-3 text-base">Processing failed</p>
          <p className="text-red-400/80 text-sm max-w-lg mx-auto">{error}</p>
        </div>
      ) : (
        <div className="rounded-2xl bg-white/[0.03] border border-white/10 p-9 sm:p-10">
          <div className="flex items-center gap-3 mb-7">
            <div className="w-2.5 h-2.5 rounded-full bg-violet-400 animate-pulse" />
            <p className="text-white font-semibold text-base">{message}</p>
          </div>

          <div className="w-full h-2.5 bg-white/10 rounded-full overflow-hidden mb-3 relative">
            <div
              className="h-full bg-gradient-to-r from-violet-500 via-fuchsia-500 to-pink-500 rounded-full transition-all duration-700 relative overflow-hidden shadow-sm shadow-violet-500/50"
              style={{ width: `${progress}%` }}
            >
              <div className="absolute inset-0 bg-white/20 animate-pulse" />
            </div>
          </div>
          <div className="flex justify-between text-xs text-white/40 mt-1">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-ping inline-block" />
              Processing
            </span>
            <span className="font-mono text-violet-300 font-medium">{progress}%</span>
          </div>
        </div>
      )}
    </div>
  );
}
