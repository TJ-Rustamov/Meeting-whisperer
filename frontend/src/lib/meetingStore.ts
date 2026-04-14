export interface TranscriptEntry {
  id: string;
  speaker: string;
  source?: "mic" | "system" | "mixed";
  text: string;
  timestamp: number;
  startTime: number;
  endTime: number;
}

export interface Meeting {
  id: string;
  title: string;
  date: string;
  duration: number;
  transcript: TranscriptEntry[];
  summary?: string;
  audioUrl?: string;
  videoUrl?: string;
  processedStatus: "idle" | "queued" | "running" | "done" | "failed";
  processedDetail?: string;
  processedProgressPct?: number;
  processedStartedAt?: string;
  processedFinishedAt?: string;
  processedError?: string;
  hasProcessedTranscript: boolean;
}

export interface ProcessedTranscriptEntry {
  id: string;
  speaker: string;
  source?: "mic" | "system" | "mixed";
  text: string;
  startTime: number;
  endTime: number;
}

export interface ProcessedTranscript {
  meetingId: string;
  status: "idle" | "queued" | "running" | "done" | "failed";
  startedAt?: string;
  finishedAt?: string;
  error?: string;
  segments: ProcessedTranscriptEntry[];
}

export interface AppSettings {
  llmProvider: "openai" | "gemini";
  llmApiKey: string;
  profile: {
    name: string;
    email: string;
    avatarUrl: string;
  };
}

interface ApiTranscriptSegment {
  id: number;
  speaker_label: string;
  start_time: number;
  end_time: number;
  text: string;
}

interface ApiMeeting {
  id: number;
  title: string;
  created_at: string;
  duration_seconds: number | null;
  audio_url: string | null;
  video_url: string | null;
  summary_text: string | null;
  processed_status: "idle" | "queued" | "running" | "done" | "failed";
  processed_started_at: string | null;
  processed_finished_at: string | null;
  processed_error: string | null;
  has_processed_transcript: boolean;
  transcript_segments: ApiTranscriptSegment[];
}

interface ApiProcessedTranscript {
  meeting_id: number;
  processed_status: "idle" | "queued" | "running" | "done" | "failed";
  processed_started_at: string | null;
  processed_finished_at: string | null;
  processed_error: string | null;
  segments: ApiTranscriptSegment[];
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function audioUrl(path: string | null): string | undefined {
  if (!path) return undefined;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${API_BASE}${path}`;
}

function mapMeeting(m: ApiMeeting): Meeting {
  const parseSpeakerAndSource = (
    raw: string
  ): { speaker: string; source?: "mic" | "system" | "mixed" } => {
    const value = (raw || "").trim();
    const idx = value.indexOf(":");
    if (idx <= 0) return { speaker: value || "speaker" };
    const maybeSource = value.slice(0, idx).toLowerCase();
    const speaker = value.slice(idx + 1).trim() || "speaker";
    if (maybeSource === "mic" || maybeSource === "system" || maybeSource === "mixed") {
      return { speaker, source: maybeSource };
    }
    return { speaker: value || "speaker" };
  };

  return {
    id: String(m.id),
    title: m.title,
    date: m.created_at,
    duration: m.duration_seconds ?? 0,
    summary: m.summary_text ?? undefined,
    audioUrl: audioUrl(m.audio_url),
    videoUrl: audioUrl(m.video_url),
    processedStatus: m.processed_status,
    processedStartedAt: m.processed_started_at ?? undefined,
    processedFinishedAt: m.processed_finished_at ?? undefined,
    processedError: m.processed_error ?? undefined,
    hasProcessedTranscript: m.has_processed_transcript,
    transcript: m.transcript_segments.map((s) => {
      const parsed = parseSpeakerAndSource(s.speaker_label);
      return {
        id: String(s.id),
        speaker: parsed.speaker,
        source: parsed.source,
        text: s.text,
        timestamp: Math.floor(s.start_time),
        startTime: s.start_time,
        endTime: s.end_time,
      };
    }),
  };
}

function mapProcessedTranscript(t: ApiProcessedTranscript): ProcessedTranscript {
  const parseSpeakerAndSource = (
    raw: string
  ): { speaker: string; source?: "mic" | "system" | "mixed" } => {
    const value = (raw || "").trim();
    const idx = value.indexOf(":");
    if (idx <= 0) return { speaker: value || "speaker" };
    const maybeSource = value.slice(0, idx).toLowerCase();
    const speaker = value.slice(idx + 1).trim() || "speaker";
    if (maybeSource === "mic" || maybeSource === "system" || maybeSource === "mixed") {
      return { speaker, source: maybeSource };
    }
    return { speaker: value || "speaker" };
  };

  return {
    meetingId: String(t.meeting_id),
    status: t.processed_status,
    startedAt: t.processed_started_at ?? undefined,
    finishedAt: t.processed_finished_at ?? undefined,
    error: t.processed_error ?? undefined,
    segments: t.segments.map((s) => {
      const parsed = parseSpeakerAndSource(s.speaker_label);
      return {
        id: String(s.id),
        speaker: parsed.speaker,
        source: parsed.source,
        text: s.text,
        startTime: s.start_time,
        endTime: s.end_time,
      };
    }),
  };
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function getTranscribeWsUrl(meetingId: string, source?: "mic" | "system" | "mixed"): string {
  const base = new URL(API_BASE);
  const protocol = base.protocol === "https:" ? "wss:" : "ws:";
  const url = new URL(`${protocol}//${base.host}/ws/meetings/${meetingId}/transcribe`);
  if (source) {
    url.searchParams.set("source", source);
  }
  return url.toString();
}

export async function createMeeting(title?: string): Promise<Meeting> {
  const payload = await api<ApiMeeting>("/api/meetings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return mapMeeting(payload);
}

export async function getMeetings(): Promise<Meeting[]> {
  const payload = await api<ApiMeeting[]>("/api/meetings");
  return payload.map(mapMeeting);
}

export async function getMeeting(id: string): Promise<Meeting> {
  const payload = await api<ApiMeeting>(`/api/meetings/${id}`);
  return mapMeeting(payload);
}

export async function deleteMeeting(id: string): Promise<void> {
  await api<{ ok: boolean }>(`/api/meetings/${id}`, { method: "DELETE" });
}

export async function renameMeeting(id: string, title: string): Promise<Meeting> {
  const payload = await api<ApiMeeting>(`/api/meetings/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return mapMeeting(payload);
}

export async function uploadMeetingAudio(id: string, audioBlob: Blob): Promise<Meeting> {
  const form = new FormData();
  form.append("file", audioBlob, "meeting.webm");
  const payload = await api<ApiMeeting>(`/api/meetings/${id}/audio`, {
    method: "POST",
    body: form,
  });
  return mapMeeting(payload);
}

export async function uploadMeetingVideo(id: string, videoBlob: Blob): Promise<Meeting> {
  const form = new FormData();
  form.append("file", videoBlob, "screen.webm");
  const payload = await api<ApiMeeting>(`/api/meetings/${id}/video`, {
    method: "POST",
    body: form,
  });
  return mapMeeting(payload);
}

export async function triggerMeetingPostProcess(id: string): Promise<Meeting> {
  const payload = await api<ApiMeeting>(`/api/meetings/${id}/process`, {
    method: "POST",
  });
  return mapMeeting(payload);
}

export async function restartMeetingPostProcess(id: string): Promise<Meeting> {
  const payload = await api<ApiMeeting>(`/api/meetings/${id}/process/restart`, {
    method: "POST",
  });
  return mapMeeting(payload);
}

export async function stopMeetingPostProcess(id: string): Promise<Meeting> {
  const payload = await api<ApiMeeting>(`/api/meetings/${id}/process/stop`, {
    method: "POST",
  });
  return mapMeeting(payload);
}

export async function getProcessedTranscript(id: string): Promise<ProcessedTranscript> {
  const payload = await api<ApiProcessedTranscript>(`/api/meetings/${id}/processed-transcript`);
  return mapProcessedTranscript(payload);
}

export async function getSettings(): Promise<AppSettings> {
  return api<AppSettings>("/api/settings");
}

export async function saveSettings(settings: AppSettings): Promise<AppSettings> {
  return api<AppSettings>("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
}

export async function shutdownApp(): Promise<void> {
  await api<{ ok: boolean; message: string }>("/api/settings/shutdown", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
}

export function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}
