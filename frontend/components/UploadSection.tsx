"use client";

import { useRef, useState, useCallback } from "react";

interface UploadSectionProps {
  onUploadComplete: (jobId: string, file: File) => void;
}

const ACCEPTED = [".mp4", ".mov", ".webm"];
const MAX_SIZE_MB = 500;

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export default function UploadSection({ onUploadComplete }: UploadSectionProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const handleFile = useCallback((f: File) => {
    const ext = "." + f.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED.includes(ext)) {
      setError(`Unsupported format. Please use ${ACCEPTED.join(", ")}`);
      return;
    }
    if (f.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`File too large (${formatSize(f.size)}). Max ${MAX_SIZE_MB}MB.`);
      return;
    }
    setError("");
    setFile(f);
    setUploadProgress(0);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const dropped = e.dataTransfer.files[0];
      if (dropped) handleFile(dropped);
    },
    [handleFile]
  );

  const onInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected) handleFile(selected);
    },
    [handleFile]
  );

  const handleCreate = async () => {
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const { uploadVideo, startProcessing } = await import("@/lib/api");
      const { job_id } = await uploadVideo(file, setUploadProgress);
      await startProcessing(job_id);
      onUploadComplete(job_id, file);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setUploading(false);
    }
  };

  return (
    <div className="w-full max-w-lg mx-auto my-4 sm:my-6">
      {/* Drop zone */}
      <div
        onClick={() => !uploading && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`
          relative cursor-pointer rounded-2xl border-2 border-dashed text-center
          transition-all duration-300 group
          ${file ? "p-7 sm:p-9" : "p-10 sm:p-14"}
          ${dragging
            ? "border-violet-400 bg-violet-500/10 scale-[1.01]"
            : file
            ? "border-violet-500/60 bg-violet-500/5 shadow-lg shadow-violet-500/5"
            : "border-white/10 bg-white/[0.02] hover:border-violet-500/40 hover:bg-white/[0.04]"
          }
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".mp4,.mov,.webm"
          className="hidden"
          onChange={onInputChange}
          disabled={uploading}
        />

        {!file ? (
          <div className="flex flex-col items-center">
            <div className="mb-6">
              <div
                className={`
                w-20 h-20 rounded-2xl flex items-center justify-center
                bg-gradient-to-br from-violet-600/20 to-fuchsia-600/20
                border border-violet-500/20 group-hover:border-violet-400/40
                transition-all duration-300
              `}
              >
                <svg className="w-10 h-10 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"
                  />
                </svg>
              </div>
            </div>

            <p className="text-xl font-semibold text-white mb-2">Drop your video here</p>
            <p className="text-sm text-white/40 mb-6">or click to browse</p>

            <div className="flex items-center justify-center gap-2 mb-4">
              {ACCEPTED.map((ext) => (
                <span key={ext} className="text-xs px-2.5 py-1 rounded-md bg-white/5 text-white/50 font-mono">
                  {ext}
                </span>
              ))}
            </div>

            <p className="text-xs text-white/30">Recommended: videos under 2 minutes for best results</p>
          </div>
        ) : (
          <div className="text-left py-2 px-1">
            <div className="flex items-center gap-5">
              <div className="w-13 h-13 rounded-2xl bg-gradient-to-br from-violet-600 to-fuchsia-600 flex items-center justify-center flex-shrink-0 shadow-md shadow-violet-500/30">
                <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <div className="flex-1 min-w-0 pr-2">
                <p className="text-white font-semibold truncate text-base sm:text-lg mb-1">{file.name}</p>
                <p className="text-white/45 text-sm font-medium">{formatSize(file.size)}</p>
              </div>
              {!uploading && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                    setUploadProgress(0);
                  }}
                  className="text-white/35 hover:text-white/80 transition-colors p-2 rounded-lg hover:bg-white/5 cursor-pointer flex-shrink-0"
                  title="Remove file"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>

            {uploading && (
              <div className="mt-7">
                <div className="flex items-center justify-between text-xs text-white/40 mb-2">
                  <span>Uploading...</span>
                  <span className="font-mono">{uploadProgress}%</span>
                </div>
                <div className="w-full h-2.5 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="mt-5 flex items-center gap-3 text-red-400 text-sm bg-red-500/10 rounded-xl px-5 py-4 border border-red-500/20">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {file && !uploading && (
        <button
          id="create-directors-cut-btn"
          onClick={handleCreate}
          className="
            mt-8 sm:mt-10 w-full py-4 sm:py-4.5 rounded-2xl font-semibold text-base sm:text-lg
            bg-gradient-to-r from-violet-600 to-fuchsia-600
            hover:from-violet-500 hover:to-fuchsia-500
            text-white transition-all duration-200
            shadow-xl shadow-violet-500/25 hover:shadow-violet-500/40
            hover:scale-[1.01] active:scale-[0.99] cursor-pointer
          "
        >
          ✦ Create Director&apos;s Cut
        </button>
      )}
    </div>
  );
}
