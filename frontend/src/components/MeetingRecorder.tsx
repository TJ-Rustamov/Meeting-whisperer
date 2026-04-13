import { useState, useRef, useCallback, useEffect } from "react";
import { Mic, Square, Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import {
  TranscriptEntry,
  createMeeting,
  formatTime,
  getTranscribeWsUrl,
  uploadMeetingAudio,
  uploadMeetingVideo,
} from "@/lib/meetingStore";
import { toast } from "sonner";

interface MeetingRecorderProps {
  onStop: (meetingId: string) => void;
  onRecordingStateChange?: (isRecording: boolean) => void;
}
type SttSourceLabel = "mic" | "system";

interface SessionConfig {
  screen: boolean;
  audio: boolean;
  transcript: boolean;
}

const EMPTY_SESSION_CONFIG: SessionConfig = {
  screen: false,
  audio: false,
  transcript: false,
};

export function MeetingRecorder({ onStop, onRecordingStateChange }: MeetingRecorderProps) {
  const PCM_INPUT_GAIN = 1.6;
  const MIC_STORAGE_KEY = "meeting_whisperer_mic_device_id";
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [partialBySource, setPartialBySource] = useState<Partial<Record<SttSourceLabel, string>>>({});
  const [isStarting, setIsStarting] = useState(false);
  const [captureScreen, setCaptureScreen] = useState(true);
  const [captureMic, setCaptureMic] = useState(true);
  const [captureSystemAudio, setCaptureSystemAudio] = useState(true);
  const [liveTranscript, setLiveTranscript] = useState(true);
  const [micGain, setMicGain] = useState(1);
  const [systemGain, setSystemGain] = useState(1);
  const [availableMics, setAvailableMics] = useState<MediaDeviceInfo[]>([]);
  const [selectedMicId, setSelectedMicId] = useState<string>("");

  const timerRef = useRef<ReturnType<typeof setInterval>>();
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const audioRecorderRef = useRef<MediaRecorder | null>(null);
  const videoRecorderRef = useRef<MediaRecorder | null>(null);
  const sourceStreamsRef = useRef<MediaStream[]>([]);
  const audioRecordingStreamRef = useRef<MediaStream | null>(null);
  const mixedArchiveTrackRef = useRef<MediaStreamTrack | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const scriptNodesRef = useRef<ScriptProcessorNode[]>([]);
  const sourceNodesRef = useRef<MediaStreamAudioSourceNode[]>([]);
  const wsRefs = useRef<Partial<Record<SttSourceLabel, WebSocket>>>({});
  const audioChunksRef = useRef<BlobPart[]>([]);
  const videoChunksRef = useRef<BlobPart[]>([]);
  const meetingIdRef = useRef<string | null>(null);
  const isPausedRef = useRef(false);
  const wsPacketsRef = useRef(0);
  const audioPacketsRef = useRef(0);
  const sessionClosedSourcesRef = useRef<Set<SttSourceLabel>>(new Set());
  const sessionConfigRef = useRef<SessionConfig>(EMPTY_SESSION_CONFIG);

  const debug = (...args: unknown[]) => {
    console.debug("[MeetingRecorder]", ...args);
  };

  const refreshMicDevices = useCallback(async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const mics = devices.filter((d) => d.kind === "audioinput");
      setAvailableMics(mics);
      if (!selectedMicId && mics.length > 0) {
        const remembered = localStorage.getItem(MIC_STORAGE_KEY);
        const preferred =
          (remembered && mics.find((m) => m.deviceId === remembered)?.deviceId) || mics[0].deviceId;
        setSelectedMicId(preferred);
      }
    } catch (error) {
      debug("enumerateDevices failed", error);
    }
  }, [selectedMicId]);

  const toPcm16Buffer = (input: Float32Array, inputSampleRate: number, targetSampleRate = 16000): ArrayBuffer => {
    const ratio = inputSampleRate / targetSampleRate;
    const outputLength = Math.max(1, Math.round(input.length / ratio));
    const output = new Int16Array(outputLength);
    let outputIndex = 0;
    let inputIndex = 0;
    while (outputIndex < outputLength) {
      const nextInputIndex = Math.min(input.length, Math.round((outputIndex + 1) * ratio));
      let sum = 0;
      let count = 0;
      for (let i = inputIndex; i < nextInputIndex; i += 1) {
        sum += input[i];
        count += 1;
      }
      const sample = count > 0 ? sum / count : 0;
      const boosted = sample * PCM_INPUT_GAIN;
      const softened = Math.tanh(boosted);
      const clamped = Math.max(-1, Math.min(1, softened));
      output[outputIndex] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
      outputIndex += 1;
      inputIndex = nextInputIndex;
    }
    return output.buffer;
  };

  const stopAllSourceStreams = () => {
    sourceStreamsRef.current.forEach((stream) => {
      stream.getTracks().forEach((track) => track.stop());
    });
    sourceStreamsRef.current = [];
  };

  const resetSessionResources = () => {
    scriptNodesRef.current.forEach((node) => node.disconnect());
    sourceNodesRef.current.forEach((node) => node.disconnect());
    audioRecordingStreamRef.current?.getTracks().forEach((track) => track.stop());
    stopAllSourceStreams();
    void audioContextRef.current?.close();
    audioRecorderRef.current = null;
    videoRecorderRef.current = null;
    audioContextRef.current = null;
    mixedArchiveTrackRef.current = null;
    scriptNodesRef.current = [];
    sourceNodesRef.current = [];
    audioRecordingStreamRef.current = null;
    Object.values(wsRefs.current).forEach((ws) => ws?.close());
    wsRefs.current = {};
    sessionClosedSourcesRef.current.clear();
  };

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript, partialBySource]);

  useEffect(() => {
    onRecordingStateChange?.(isRecording);
  }, [isRecording, onRecordingStateChange]);

  useEffect(() => {
    refreshMicDevices();
    const onDeviceChange = () => {
      void refreshMicDevices();
    };
    navigator.mediaDevices?.addEventListener?.("devicechange", onDeviceChange);
    return () => {
      navigator.mediaDevices?.removeEventListener?.("devicechange", onDeviceChange);
    };
  }, [refreshMicDevices]);

  const startRecording = useCallback(async () => {
    setIsStarting(true);
    debug("startRecording requested", {
      captureScreen,
      captureMic,
      captureSystemAudio,
      liveTranscript,
      micGain,
      systemGain,
    });
    try {
      const hasConfiguredAudioSource = captureMic || captureSystemAudio;
      const resolvedRecordAudio = hasConfiguredAudioSource;

      if (!captureScreen && !hasConfiguredAudioSource && !liveTranscript) {
        toast.error("Enable at least one source: Screen, Mic, System Audio, or Transcript.");
        return;
      }
      if (liveTranscript && !hasConfiguredAudioSource) {
        toast.error("Live transcript needs Mic or System Audio to be ON.");
        return;
      }

      const created = await createMeeting(`Meeting ${new Date().toLocaleString()}`);
      meetingIdRef.current = created.id;
      sessionConfigRef.current = {
        screen: captureScreen,
        audio: resolvedRecordAudio,
        transcript: liveTranscript,
      };

      debug("meeting created", {
        meetingId: created.id,
        config: sessionConfigRef.current,
      });

      setIsRecording(true);
      setIsPaused(false);
      isPausedRef.current = false;
      setElapsed(0);
      setTranscript([]);
      setPartialBySource({});
      audioChunksRef.current = [];
      videoChunksRef.current = [];
      wsPacketsRef.current = 0;
      audioPacketsRef.current = 0;
      sessionClosedSourcesRef.current.clear();

      const needsAudioSource = hasConfiguredAudioSource || liveTranscript;
      let displayStream: MediaStream | null = null;
      const sourceDescriptors: Array<{ stream: MediaStream; kind: SttSourceLabel; gain: number }> = [];

      if (captureScreen) {
        displayStream = await navigator.mediaDevices.getDisplayMedia({
          video: {
            frameRate: { ideal: 12, max: 15 },
            width: { ideal: 1280, max: 1920 },
            height: { ideal: 720, max: 1080 },
          },
          audio: captureSystemAudio,
        });
        sourceStreamsRef.current.push(displayStream);
        if (captureSystemAudio && displayStream.getAudioTracks().length > 0) {
          sourceDescriptors.push({ stream: displayStream, kind: "system", gain: systemGain });
        }
        const videoTrack = displayStream.getVideoTracks()[0];
        if (!videoTrack) {
          throw new Error("Screen capture started without a video track.");
        }
      } else if (captureSystemAudio) {
        try {
          const desktopAudioStream = await navigator.mediaDevices.getDisplayMedia({
            // Browser APIs require video to request display media; we immediately stop it
            // so this mode acts as desktop-audio-only capture.
            video: true,
            audio: true,
          });
          const hasDesktopAudio = desktopAudioStream.getAudioTracks().length > 0;
          desktopAudioStream.getVideoTracks().forEach((track) => track.stop());
          if (hasDesktopAudio) {
            sourceStreamsRef.current.push(desktopAudioStream);
            sourceDescriptors.push({ stream: desktopAudioStream, kind: "system", gain: systemGain });
            toast.info("Desktop audio capture enabled without video recording.");
          } else {
            desktopAudioStream.getTracks().forEach((track) => track.stop());
            toast.warning("Desktop share did not include system audio.");
          }
        } catch {
          toast.warning("Desktop audio capture was skipped.");
        }
      }

      if (captureMic) {
        const strictMicConstraints: MediaTrackConstraints = {
          ...(selectedMicId ? { deviceId: { exact: selectedMicId } } : {}),
          channelCount: { ideal: 1 },
          sampleRate: { ideal: 48000 },
          sampleSize: { ideal: 16 },
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: false,
        };

        let micStream: MediaStream | null = null;
        try {
          micStream = await navigator.mediaDevices.getUserMedia({ audio: strictMicConstraints });
        } catch {
          // Retry with generic constraints to handle stricter browser/device combinations.
          micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        }

        try {
          if (!micStream) {
            throw new Error("No microphone stream acquired.");
          }
          sourceStreamsRef.current.push(micStream);
          sourceDescriptors.push({ stream: micStream, kind: "mic", gain: micGain });
          const micAvailable = micStream.getAudioTracks().length > 0;
          if (!micAvailable) {
            throw new Error("Microphone stream has no audio tracks.");
          }
        } catch (error) {
          throw new Error("Microphone access failed. Allow mic permission or turn Mic OFF.");
        }
      }

      const audioTrackCount = sourceDescriptors.reduce(
        (count, item) => count + item.stream.getAudioTracks().length,
        0
      );
      if (needsAudioSource && audioTrackCount === 0) {
        throw new Error("No audio input available for recording/transcription.");
      }

      if (liveTranscript) {
        const sttSources = Array.from(new Set(sourceDescriptors.map((s) => s.kind)));
        sttSources.forEach((source) => {
          const ws = new WebSocket(getTranscribeWsUrl(created.id, source));
          wsRefs.current[source] = ws;
          ws.onopen = () => {
            debug("websocket opened", { source, url: getTranscribeWsUrl(created.id, source) });
            ws.send(JSON.stringify({ action: "start" }));
          };
          ws.onmessage = (event) => {
            try {
              const payload = JSON.parse(event.data);
              wsPacketsRef.current += 1;
              const payloadSource = (payload.source_label as SttSourceLabel | undefined) ?? source;
              if (payload.event === "partial_transcript") {
                setPartialBySource((prev) => ({ ...prev, [payloadSource]: payload.text ?? "" }));
              } else if (payload.event === "final_segment") {
                const entry: TranscriptEntry = {
                  id: String(payload.id ?? crypto.randomUUID()),
                  speaker: payload.speaker_label ?? "speaker",
                  source: payloadSource,
                  text: payload.text ?? "",
                  timestamp: Math.floor(Number(payload.start_time ?? 0)),
                  startTime: Number(payload.start_time ?? 0),
                  endTime: Number(payload.end_time ?? 0),
                };
                setTranscript((prev) => [...prev, entry]);
                setPartialBySource((prev) => ({ ...prev, [payloadSource]: "" }));
              } else if (payload.event === "error") {
                toast.error(payload.message ?? "Streaming error");
              } else if (payload.event === "session_closed") {
                sessionClosedSourcesRef.current.add(payloadSource);
              }
            } catch {
              // ignore invalid frames
            }
          };
          ws.onerror = () => {
            toast.error(`WebSocket transcription failed for ${source} source`);
          };
        });
      }

      if (needsAudioSource) {
        const audioContext = new AudioContext();
        await audioContext.resume();
        audioContextRef.current = audioContext;

        const archiveGain = audioContext.createGain();
        archiveGain.gain.value = 1;

        const sourceNodes = sourceDescriptors
          .map(({ stream, kind, gain }) => {
            const audioOnly = new MediaStream(stream.getAudioTracks());
            if (audioOnly.getAudioTracks().length === 0) {
              return null;
            }
            return { node: audioContext.createMediaStreamSource(audioOnly), kind, gain };
          })
          .filter(
            (entry): entry is { node: MediaStreamAudioSourceNode; kind: SttSourceLabel; gain: number } =>
              entry !== null
          );

        sourceNodes.forEach(({ node, gain, kind }) => {
          const perSourceGain = audioContext.createGain();
          perSourceGain.gain.value = gain;
          node.connect(perSourceGain);
          // Keep archival recording close to raw mix so post-process diarization remains effective.
          perSourceGain.connect(archiveGain);
        });
        sourceNodesRef.current = sourceNodes.map(({ node }) => node);

        if (resolvedRecordAudio) {
          const recordingDestination = audioContext.createMediaStreamDestination();
          archiveGain.connect(recordingDestination);
          const recordingStream = new MediaStream(recordingDestination.stream.getAudioTracks());
          audioRecordingStreamRef.current = recordingStream;
          mixedArchiveTrackRef.current = recordingStream.getAudioTracks()[0] ?? null;

          const preferredAudioMime = [
            "audio/webm;codecs=opus",
            "audio/webm",
            "audio/ogg;codecs=opus",
          ].find((mime) => MediaRecorder.isTypeSupported(mime));

          const audioRecorder = new MediaRecorder(
            recordingStream,
            preferredAudioMime ? { mimeType: preferredAudioMime } : undefined
          );
          audioRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
              audioChunksRef.current.push(event.data);
            }
          };
          audioRecorder.start(1000);
          audioRecorderRef.current = audioRecorder;
        }

        if (liveTranscript) {
          const silentGain = audioContext.createGain();
          silentGain.gain.value = 0;
          scriptNodesRef.current = [];

          sourceNodes.forEach(({ node, kind, gain }) => {
            const ws = wsRefs.current[kind];
            if (!ws) return;

            const highPass = audioContext.createBiquadFilter();
            highPass.type = "highpass";
            highPass.frequency.value = 80;
            highPass.Q.value = 0.7;

            const lowPass = audioContext.createBiquadFilter();
            lowPass.type = "lowpass";
            lowPass.frequency.value = 7600;
            lowPass.Q.value = 0.7;

            const compressor = audioContext.createDynamicsCompressor();
            compressor.threshold.value = -22;
            compressor.knee.value = 18;
            compressor.ratio.value = 3;
            compressor.attack.value = 0.003;
            compressor.release.value = 0.2;

            const sttGain = audioContext.createGain();
            const sttWeight = kind === "mic" ? 1.15 : 1.0;
            sttGain.gain.value = gain * sttWeight;

            const scriptNode = audioContext.createScriptProcessor(4096, 1, 1);
            scriptNode.onaudioprocess = (event) => {
              if (isPausedRef.current) return;
              if (ws.readyState !== WebSocket.OPEN) return;
              const input = event.inputBuffer.getChannelData(0);
              const pcm = toPcm16Buffer(input, audioContext.sampleRate, 16000);
              ws.send(pcm);
              audioPacketsRef.current += 1;
            };

            node.connect(sttGain);
            sttGain.connect(highPass);
            highPass.connect(lowPass);
            lowPass.connect(compressor);
            compressor.connect(scriptNode);
            scriptNode.connect(silentGain);
            scriptNodesRef.current.push(scriptNode);
          });

          silentGain.connect(audioContext.destination);
          if (scriptNodesRef.current.length === 0) {
            toast.error("Live transcription pipeline failed to initialize.");
          }
        }
      }

      if (captureScreen && displayStream) {
        const videoTracks = displayStream.getVideoTracks();
        const mixedArchiveTrack = mixedArchiveTrackRef.current;
        const videoAudioTracks =
          mixedArchiveTrack && mixedArchiveTrack.readyState === "live"
            ? [mixedArchiveTrack]
            : displayStream.getAudioTracks();
        const videoStream = new MediaStream([...videoTracks, ...videoAudioTracks]);

        const preferredVideoMime = [
          "video/webm;codecs=vp8,opus",
          "video/webm;codecs=vp9,opus",
          "video/webm",
        ].find((mime) => MediaRecorder.isTypeSupported(mime));

        const videoRecorder = new MediaRecorder(
          videoStream,
          preferredVideoMime ? { mimeType: preferredVideoMime } : undefined
        );
        videoRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            videoChunksRef.current.push(event.data);
          }
        };
        videoRecorder.start(1500);
        videoRecorderRef.current = videoRecorder;
      }

      timerRef.current = setInterval(() => {
        setElapsed((e) => e + 1);
      }, 1000);
    } catch (error) {
      console.error(error);
      toast.error("Unable to start recording. Check selected toggles and browser permissions.");
      Object.values(wsRefs.current).forEach((ws) => ws?.close());
      wsRefs.current = {};
      resetSessionResources();
      sessionConfigRef.current = EMPTY_SESSION_CONFIG;
      setIsRecording(false);
      void refreshMicDevices();
    } finally {
      setIsStarting(false);
    }
  }, [
    captureScreen,
    captureMic,
    captureSystemAudio,
    liveTranscript,
    micGain,
    systemGain,
    refreshMicDevices,
    selectedMicId,
  ]);

  const pauseRecording = () => {
    if (!isRecording) return;
    setIsPaused(true);
    isPausedRef.current = true;
    clearInterval(timerRef.current);

    if (sessionConfigRef.current.transcript) {
      Object.values(wsRefs.current).forEach((ws) => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ action: "pause" }));
        }
      });
    }
    if (audioRecorderRef.current?.state === "recording") {
      audioRecorderRef.current.pause();
    }
    if (videoRecorderRef.current?.state === "recording") {
      videoRecorderRef.current.pause();
    }
  };

  const resumeRecording = () => {
    if (!isRecording) return;
    setIsPaused(false);
    isPausedRef.current = false;

    if (sessionConfigRef.current.transcript) {
      Object.values(wsRefs.current).forEach((ws) => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ action: "resume" }));
        }
      });
    }
    if (audioRecorderRef.current?.state === "paused") {
      audioRecorderRef.current.resume();
    }
    if (videoRecorderRef.current?.state === "paused") {
      videoRecorderRef.current.resume();
    }

    timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
  };

  const stopRecorderIfNeeded = (recorder: MediaRecorder | null) =>
    new Promise<void>((resolve) => {
      if (!recorder || recorder.state === "inactive") {
        resolve();
        return;
      }
      recorder.onstop = () => resolve();
      recorder.stop();
    });

  const stopRecording = async () => {
    clearInterval(timerRef.current);
    setIsPaused(false);
    isPausedRef.current = false;

    const meetingId = meetingIdRef.current;
    if (!meetingId) {
      setIsRecording(false);
      return;
    }

    try {
      if (sessionConfigRef.current.transcript) {
        const activeSources = Object.keys(wsRefs.current) as SttSourceLabel[];
        activeSources.forEach((source) => {
          const ws = wsRefs.current[source];
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: "stop" }));
          }
        });
        await new Promise<void>((resolve) => {
          const started = Date.now();
          const waitForAck = () => {
            const closedCount = activeSources.filter((source) => sessionClosedSourcesRef.current.has(source)).length;
            if (closedCount >= activeSources.length) {
              resolve();
              return;
            }
            if (Date.now() - started > 2000) {
              resolve();
              return;
            }
            setTimeout(waitForAck, 50);
          };
          waitForAck();
        });
      }
      Object.values(wsRefs.current).forEach((ws) => ws?.close());
      wsRefs.current = {};

      await Promise.all([
        stopRecorderIfNeeded(audioRecorderRef.current),
        stopRecorderIfNeeded(videoRecorderRef.current),
      ]);

      if (sessionConfigRef.current.audio) {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        if (audioBlob.size > 0) {
          await uploadMeetingAudio(meetingId, audioBlob);
        }
      }

      if (sessionConfigRef.current.screen) {
        const videoBlob = new Blob(videoChunksRef.current, { type: "video/webm" });
        if (videoBlob.size > 0) {
          await uploadMeetingVideo(meetingId, videoBlob);
        }
      }

      onStop(meetingId);
    } catch (error) {
      console.error(error);
      toast.error("Failed to finalize meeting");
    } finally {
      resetSessionResources();
      meetingIdRef.current = null;
      sessionConfigRef.current = EMPTY_SESSION_CONFIG;
      setIsRecording(false);
      setPartialBySource({});
    }
  };

  useEffect(() => {
    return () => {
      clearInterval(timerRef.current);
      Object.values(wsRefs.current).forEach((ws) => ws?.close());
      resetSessionResources();
    };
  }, []);

  if (!isRecording) {
    return (
      <div className="flex-1 flex items-center justify-center p-4 md:p-8">
        <div className="w-full max-w-2xl rounded-3xl border border-border/80 bg-card/70 backdrop-blur-sm p-5 md:p-7 shadow-xl space-y-6">
          <div className="flex items-center justify-center">
            <Button
              variant="hero"
              size="lg"
              className="h-28 w-28 rounded-full text-base shadow-lg"
              onClick={startRecording}
              disabled={isStarting}
            >
              <div className="flex flex-col items-center gap-1">
                <Mic className="h-8 w-8" />
                <span className="text-xs tracking-wide">RECORD</span>
              </div>
            </Button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <Button type="button" variant={captureScreen ? "default" : "outline"} onClick={() => setCaptureScreen((v) => !v)}>
              Screen {captureScreen ? "ON" : "OFF"}
            </Button>
            <Button type="button" variant={captureMic ? "default" : "outline"} onClick={() => setCaptureMic((v) => !v)}>
              Mic {captureMic ? "ON" : "OFF"}
            </Button>
            <Button
              type="button"
              variant={captureSystemAudio ? "default" : "outline"}
              onClick={() => setCaptureSystemAudio((v) => !v)}
            >
              System {captureSystemAudio ? "ON" : "OFF"}
            </Button>
            <Button
              type="button"
              variant={liveTranscript ? "default" : "outline"}
              onClick={() => setLiveTranscript((v) => !v)}
            >
              Transcript {liveTranscript ? "ON" : "OFF"}
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-xl border border-border/70 bg-background/70 p-3 space-y-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Desktop Audio</span>
                <span>{Math.round(systemGain * 100)}%</span>
              </div>
              <Slider
                min={0}
                max={2}
                step={0.01}
                value={[systemGain]}
                onValueChange={(values) => setSystemGain(values[0] ?? 1)}
                disabled={!captureSystemAudio}
                aria-label="Desktop audio volume"
              />
            </div>

            <div className="rounded-xl border border-border/70 bg-background/70 p-3 space-y-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Mic Audio</span>
                <span>{Math.round(micGain * 100)}%</span>
              </div>
              <Slider
                min={0}
                max={2}
                step={0.01}
                value={[micGain]}
                onValueChange={(values) => setMicGain(values[0] ?? 1)}
                disabled={!captureMic}
                aria-label="Microphone volume"
              />
            </div>
          </div>

          {captureMic && (
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground">Mic Device</div>
              <div className="flex gap-2">
                <select
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  value={selectedMicId}
                  onChange={(e) => {
                    setSelectedMicId(e.target.value);
                    localStorage.setItem(MIC_STORAGE_KEY, e.target.value);
                  }}
                >
                  {availableMics.length === 0 && <option value="">No microphone detected</option>}
                  {availableMics.map((mic, idx) => (
                    <option key={mic.deviceId || `${idx}`} value={mic.deviceId}>
                      {mic.label || `Microphone ${idx + 1}`}
                    </option>
                  ))}
                </select>
                <Button type="button" variant="outline" onClick={() => void refreshMicDevices()}>
                  Refresh
                </Button>
              </div>
            </div>
          )}

          <div className="text-center text-xs text-muted-foreground">
            {isStarting
              ? "Starting capture..."
              : "Choose sources and levels, then press RECORD."}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <div className="flex items-center justify-center gap-6 py-4 md:py-5">
          <div className="flex items-center gap-3">
            <span className="h-3 w-3 rounded-full bg-primary pulse-recording" />
            <span className="text-2xl font-mono font-semibold text-foreground">{formatTime(elapsed)}</span>
          </div>
          <div className="flex gap-2">
            {isPaused ? (
              <Button variant="outline" size="icon" onClick={resumeRecording}>
                <Play className="h-4 w-4" />
              </Button>
            ) : (
              <Button variant="outline" size="icon" onClick={pauseRecording}>
                <Pause className="h-4 w-4" />
              </Button>
            )}
            <Button variant="destructive" size="icon" onClick={stopRecording}>
              <Square className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="border-t border-border px-4 py-2 text-xs text-muted-foreground flex gap-4 justify-center">
          <span>Screen: {sessionConfigRef.current.screen ? "ON" : "OFF"}</span>
          <span>Audio: {sessionConfigRef.current.audio ? "ON" : "OFF"}</span>
          <span>Transcript: {sessionConfigRef.current.transcript ? "ON" : "OFF"}</span>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6 space-y-3 scrollbar-thin">
        {!sessionConfigRef.current.transcript && (
          <p className="text-muted-foreground text-center py-8">
            Live transcript is OFF for this session.
          </p>
        )}
        {sessionConfigRef.current.transcript && transcript.length === 0 && (
          <p className="text-muted-foreground text-center py-8">Listening... transcript will appear here</p>
        )}
        {sessionConfigRef.current.transcript && (
          <>
            <div className="space-y-2">
              <div className="text-xs uppercase tracking-wide text-muted-foreground">Mic Feed</div>
              {transcript
                .filter((entry) => entry.source === "mic" || !entry.source)
                .map((entry) => (
                  <p key={entry.id} className="text-sm text-foreground leading-relaxed">
                    {entry.text}
                  </p>
                ))}
              {(partialBySource.mic || partialBySource.mixed) && (
                <p className="text-sm text-muted-foreground leading-relaxed italic opacity-80">
                  {partialBySource.mic || partialBySource.mixed}
                </p>
              )}
            </div>

            <div className="space-y-2 pt-2">
              <div className="text-xs uppercase tracking-wide text-muted-foreground">System Feed</div>
              {transcript
                .filter((entry) => entry.source === "system")
                .map((entry) => (
                  <p key={entry.id} className="text-sm text-foreground leading-relaxed">
                    {entry.text}
                  </p>
                ))}
              {partialBySource.system && (
                <p className="text-sm text-muted-foreground leading-relaxed italic opacity-80">
                  {partialBySource.system}
                </p>
              )}
            </div>
          </>
        )}
        <div ref={transcriptEndRef} />
      </div>
    </div>
  );
}
