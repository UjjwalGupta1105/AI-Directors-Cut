const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UploadResponse {
  job_id: string;
  filename: string;
}

export interface StatusResponse {
  status: string;
  progress: number;
  message: string;
  error?: string;
}

export interface ClipInfo {
  start: number;
  end: number;
  reason: string;
  score: number;
  overlay_title?: string;
  category?: string;
}

export interface AnalysisResult {
  title: string;
  summary: string;
  clips: ClipInfo[];
  intro: string;
  outro: string;
  editing_notes: string[];
}

export interface ResultResponse {
  job_id: string;
  original_filename: string;
  output_filename: string;
  duration?: number;
  analysis: AnalysisResult;
}

export async function uploadVideo(
  file: File,
  onProgress?: (pct: number) => void
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/upload`);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          reject(new Error(err.detail || "Upload failed"));
        } catch {
          reject(new Error("Upload failed"));
        }
      }
    };

    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.send(formData);
  });
}

export async function startProcessing(jobId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/process/${jobId}`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to start processing");
  }
}

export async function getStatus(jobId: string): Promise<StatusResponse> {
  const res = await fetch(`${API_BASE}/api/status/${jobId}`);
  if (!res.ok) throw new Error(`${res.status} Failed to get status`);
  return res.json();
}

export async function getResult(jobId: string): Promise<ResultResponse> {
  const res = await fetch(`${API_BASE}/api/result/${jobId}`);
  if (!res.ok) throw new Error(`${res.status} Failed to get result`);
  return res.json();
}

export function videoUrl(filename: string): string {
  return `${API_BASE}/api/video/${filename}`;
}
