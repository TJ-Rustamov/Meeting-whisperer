import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, Maximize2, Minimize2, Pause, Play, Sparkles, Volume2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  getProcessedTranscript,
  Meeting,
  ProcessedTranscriptEntry,
  formatTime,
  restartMeetingPostProcess,
  triggerMeetingPostProcess,
  stopMeetingPostProcess,
} from "@/lib/meetingStore";
import { buildSpeakerLabelMap, speakerBadgeColor, speakerLabelFor } from "@/lib/speakerLabels";
import { toast } from "sonner";

interface MeetingDetailProps {
  meeting: Meeting;
  onBack: () => void;
  onUpdate: () => Promise<void> | void;
}

export function MeetingDetail({ meeting, onBack, onUpdate }: MeetingDetailProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackPos, setPlaybackPos] = useState(0);
  const [mediaDuration, setMediaDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [viewMode, setViewMode] = useState<"original" | "cleaned">("original");
  const [processedTranscript, setProcessedTranscript] = useState<ProcessedTranscriptEntry[]>([]);
  const [isLoadingProcessed, setIsLoadingProcessed] = useState(false);
  const [isStartingProcess, setIsStartingProcess] = useState(false);
  const [isRestartingProcess, setIsRestartingProcess] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [processedLoadError, setProcessedLoadError] = useState<string | null>(null);
  const videoWrapperRef = useRef<HTMLDivElement | null>(null);

  const getPrimaryMedia = () => videoRef.current ?? audioRef.current;
  const hasPlayableMedia = Boolean(meeting.videoUrl || meeting.audioUrl);

  const duration = useMemo(
    () => Math.max(0, meeting.duration, mediaDuration),
    [meeting.duration, mediaDuration]
  );

  const setMediaPlaybackState = (playing: boolean) => {
    setIsPlaying(playing);
  };

  const togglePlayback = async () => {
    const media = getPrimaryMedia();
    if (!media) return;
    if (isPlaying) {
      media.pause();
      setMediaPlaybackState(false);
      return;
    }
    await media.play();
    setMediaPlaybackState(true);
  };

  const seekTo = (seconds: number) => {
    const media = getPrimaryMedia();
    if (!media) return;
    const bounded = Math.max(0, Math.min(seconds, duration || 0));
    media.currentTime = bounded;
    setPlaybackPos(bounded);
  };

  const setAudioVolume = (nextVolume: number) => {
    const bounded = Math.max(0, Math.min(nextVolume, 1));
    setVolume(bounded);
    if (videoRef.current) {
      videoRef.current.volume = bounded;
    }
    if (audioRef.current) {
      audioRef.current.volume = bounded;
    }
  };

  const setAudioRate = (nextRate: number) => {
    setPlaybackRate(nextRate);
    if (videoRef.current) {
      videoRef.current.playbackRate = nextRate;
    }
    if (audioRef.current) {
      audioRef.current.playbackRate = nextRate;
    }
  };

  const syncDurationFromElement = (element: HTMLMediaElement) => {
    if (Number.isFinite(element.duration) && element.duration > 0) {
      setMediaDuration((prev) => Math.max(prev, element.duration));
    }
    if (Number.isFinite(element.currentTime) && element.currentTime > 0) {
      setMediaDuration((prev) => Math.max(prev, element.currentTime));
    }
  };

  useEffect(() => {
    setViewMode("original");
    setProcessedTranscript([]);
    setProcessedLoadError(null);
    setIsPlaying(false);
    setPlaybackPos(0);
    setMediaDuration(0);
    setIsFullscreen(false);
  }, [meeting.id]);

  useEffect(() => {
    const onFullscreenChange = () => {
      const fullscreenElement = document.fullscreenElement;
      setIsFullscreen(
        Boolean(
          fullscreenElement &&
            (fullscreenElement === videoWrapperRef.current ||
              videoWrapperRef.current?.contains(fullscreenElement))
        )
      );
    };
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", onFullscreenChange);
  }, []);

  useEffect(() => {
    if (meeting.processedStatus !== "queued" && meeting.processedStatus !== "running") {
      return;
    }
    const interval = setInterval(() => {
      void onUpdate();
    }, 2500);
    return () => clearInterval(interval);
  }, [meeting.processedStatus, onUpdate]);

  const loadProcessed = async () => {
    setIsLoadingProcessed(true);
    setProcessedLoadError(null);
    try {
      const payload = await getProcessedTranscript(meeting.id);
      setProcessedTranscript(payload.segments);
      if (payload.status !== "done") {
        setProcessedLoadError("Processed transcript is not ready yet.");
      }
    } catch (error) {
      console.error(error);
      setProcessedLoadError("Failed to load processed transcript.");
    } finally {
      setIsLoadingProcessed(false);
    }
  };

  const startProcessing = async () => {
    try {
      setIsStartingProcess(true);
      await triggerMeetingPostProcess(meeting.id);
      await onUpdate();
      toast.success("Clean & Diarize started");
    } catch (error) {
      console.error(error);
      toast.error("Failed to start processing");
    } finally {
      setIsStartingProcess(false);
    }
  };

  const restartProcessing = async () => {
    try {
      setIsRestartingProcess(true);
      await restartMeetingPostProcess(meeting.id);
      await onUpdate();
      toast.success("Processing restarted");
    } catch (error) {
      console.error(error);
      toast.error("Failed to restart processing");
    } finally {
      setIsRestartingProcess(false);
    }
  };

  const stopProcessing = async () => {
    try {
      setIsRestartingProcess(true);
      await stopMeetingPostProcess(meeting.id);
      await onUpdate();
      toast.success("Processing stopped");
    } catch (error) {
      console.error(error);
      toast.error("Failed to stop processing");
    } finally {
      setIsRestartingProcess(false);
    }
  };

  const toggleFullscreen = async () => {
    if (!videoWrapperRef.current) return;
    if (document.fullscreenElement === videoWrapperRef.current) {
      await document.exitFullscreen();
      return;
    }
    await videoWrapperRef.current.requestFullscreen();
  };

  const showToggle = meeting.processedStatus === "done" && meeting.hasProcessedTranscript;
  const showProcessButton = Boolean(meeting.audioUrl) && meeting.processedStatus === "idle";
  const showRestartButton = meeting.processedStatus !== "idle" && meeting.processedStatus !== "done";
  const activeTranscript = viewMode === "cleaned" ? processedTranscript : meeting.transcript;
  const speakerLabelMap = useMemo(
    () => buildSpeakerLabelMap(activeTranscript.map((entry) => entry.speaker)),
    [activeTranscript]
  );

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="flex items-center gap-3 p-4 md:p-6 border-b border-border">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-foreground truncate">{meeting.title}</h2>
          <p className="text-xs text-muted-foreground">
            {new Date(meeting.date).toLocaleDateString()} · {formatTime(meeting.duration)}
          </p>
        </div>
      </div>

      <div className="p-4 md:px-6 border-b border-border bg-card">
        {meeting.videoUrl && (
          <>
            <div
              ref={videoWrapperRef}
              className={`mb-4 ${
                isFullscreen
                  ? "fixed inset-0 w-screen h-screen bg-black p-0 rounded-none border-none flex flex-col justify-between z-50"
                  : "relative rounded-xl border border-border/80 bg-background p-2"
              }`}
            >
              {!isFullscreen && (
                <div className="absolute right-3 top-3 z-20">
                  <Button
                    variant="secondary"
                    size="icon"
                    onClick={toggleFullscreen}
                    aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
                  >
                    {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                  </Button>
                </div>
              )}
              {isFullscreen && (
                <div className="absolute right-4 top-4 z-50">
                  <Button
                    variant="secondary"
                    size="icon"
                    onClick={toggleFullscreen}
                    aria-label="Exit fullscreen"
                  >
                    <Minimize2 className="h-4 w-4" />
                  </Button>
                </div>
              )}
              <div className={isFullscreen ? "flex-1 flex items-center justify-center" : ""}>
                <video
                  ref={videoRef}
                  src={meeting.videoUrl}
                  controls={isFullscreen}
                  playsInline
                  className={isFullscreen ? "w-full h-full object-contain" : "w-full rounded-lg max-h-[320px] bg-black/80"}
                  onTimeUpdate={(e) => {
                    setPlaybackPos(e.currentTarget.currentTime);
                    syncDurationFromElement(e.currentTarget);
                  }}
                  onLoadedMetadata={(e) => {
                    const target = e.currentTarget;
                    target.volume = volume;
                    target.playbackRate = playbackRate;
                    syncDurationFromElement(target);
                  }}
                  onDurationChange={(e) => {
                    syncDurationFromElement(e.currentTarget);
                  }}
                  onPlay={() => setMediaPlaybackState(true)}
                  onPause={() => setMediaPlaybackState(false)}
                  onEnded={() => {
                    setMediaPlaybackState(false);
                    setPlaybackPos(0);
                  }}
                />
              </div>
              {!isFullscreen && (
                <div className="mt-2">
                  <div className="rounded-full border border-border/80 bg-background/80 px-2 py-2 shadow-sm">
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 shrink-0 rounded-full"
                        onClick={() => {
                          void togglePlayback();
                        }}
                        disabled={!hasPlayableMedia}
                      >
                        {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                      </Button>

                      <div className="flex-1 px-1">
                        <Slider
                          min={0}
                          max={Math.max(1, duration)}
                          step={0.1}
                          value={[Math.min(playbackPos, Math.max(1, duration))]}
                          onValueChange={(values) => seekTo(values[0] ?? 0)}
                          disabled={!hasPlayableMedia}
                          aria-label="Seek video"
                        />
                      </div>

                      <Popover>
                        <PopoverTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 shrink-0 rounded-full"
                            disabled={!hasPlayableMedia}
                            aria-label="Volume"
                          >
                            <Volume2 className="h-4 w-4" />
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent align="end" className="w-44 p-3">
                          <div className="space-y-2">
                            <div className="flex items-center justify-between text-xs text-muted-foreground">
                              <span>Volume</span>
                              <span>{Math.round(volume * 100)}%</span>
                            </div>
                            <Slider
                              min={0}
                              max={1}
                              step={0.01}
                              value={[volume]}
                              onValueChange={(values) => setAudioVolume(values[0] ?? 1)}
                              disabled={!hasPlayableMedia}
                              aria-label="Playback volume"
                            />
                          </div>
                        </PopoverContent>
                      </Popover>

                      <Select
                        value={String(playbackRate)}
                        onValueChange={(value) => setAudioRate(Number(value))}
                        disabled={!hasPlayableMedia}
                      >
                        <SelectTrigger className="h-8 w-[78px] rounded-full border-border/80 bg-background px-3 text-xs">
                          <SelectValue placeholder="1x" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="0.5">0.5x</SelectItem>
                          <SelectItem value="1">1x</SelectItem>
                          <SelectItem value="2">2x</SelectItem>
                          <SelectItem value="3">3x</SelectItem>
                          <SelectItem value="4">4x</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="flex justify-between text-xs text-muted-foreground px-1">
                    <span>{formatTime(playbackPos)}</span>
                    <span>{formatTime(duration)}</span>
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        {!meeting.videoUrl && (
          <>
            <div className="rounded-full border border-border/80 bg-background/80 px-2 py-2 shadow-sm">
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 shrink-0 rounded-full"
                  onClick={() => {
                    void togglePlayback();
                  }}
                  disabled={!hasPlayableMedia}
                >
                  {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                </Button>

                <div className="flex-1 px-1">
                  <Slider
                    min={0}
                    max={Math.max(1, duration)}
                    step={0.1}
                    value={[Math.min(playbackPos, Math.max(1, duration))]}
                    onValueChange={(values) => seekTo(values[0] ?? 0)}
                    disabled={!hasPlayableMedia}
                    aria-label="Seek recording"
                  />
                </div>

                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 shrink-0 rounded-full"
                      disabled={!hasPlayableMedia}
                      aria-label="Volume"
                    >
                      <Volume2 className="h-4 w-4" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent align="end" className="w-44 p-3">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>Volume</span>
                        <span>{Math.round(volume * 100)}%</span>
                      </div>
                      <Slider
                        min={0}
                        max={1}
                        step={0.01}
                        value={[volume]}
                        onValueChange={(values) => setAudioVolume(values[0] ?? 1)}
                        disabled={!hasPlayableMedia}
                        aria-label="Playback volume"
                      />
                    </div>
                  </PopoverContent>
                </Popover>

                <Select
                  value={String(playbackRate)}
                  onValueChange={(value) => setAudioRate(Number(value))}
                  disabled={!hasPlayableMedia}
                >
                  <SelectTrigger className="h-8 w-[78px] rounded-full border-border/80 bg-background px-3 text-xs">
                    <SelectValue placeholder="1x" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0.5">0.5x</SelectItem>
                    <SelectItem value="1">1x</SelectItem>
                    <SelectItem value="2">2x</SelectItem>
                    <SelectItem value="3">3x</SelectItem>
                    <SelectItem value="4">4x</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="mt-2 flex justify-between text-xs text-muted-foreground px-1">
              <span>{formatTime(playbackPos)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </>
        )}

        {!meeting.videoUrl && meeting.audioUrl && (
          <audio
            ref={audioRef}
            src={meeting.audioUrl}
            className="hidden"
            onTimeUpdate={(e) => {
              setPlaybackPos(e.currentTarget.currentTime);
              syncDurationFromElement(e.currentTarget);
            }}
            onLoadedMetadata={(e) => {
              const target = e.currentTarget;
              target.volume = volume;
              target.playbackRate = playbackRate;
              syncDurationFromElement(target);
            }}
            onDurationChange={(e) => {
              syncDurationFromElement(e.currentTarget);
            }}
            onPlay={() => setMediaPlaybackState(true)}
            onPause={() => setMediaPlaybackState(false)}
            onEnded={() => {
              setMediaPlaybackState(false);
              setPlaybackPos(0);
            }}
          />
        )}
      </div>

      <div className="px-4 md:px-6 py-3 border-b border-border">
        {meeting.summary ? (
          <div className="bg-accent/50 rounded-xl p-4">
            <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
              {meeting.summary}
            </p>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Summarization is disabled in this STT-first MVP.
          </p>
        )}
      </div>

      <div className="px-4 md:px-6 py-3 border-b border-border flex flex-wrap items-center gap-2">
        {showProcessButton && (
          <Button onClick={startProcessing} size="sm" className="gap-2" disabled={isStartingProcess || isRestartingProcess}>
            <Sparkles className="h-4 w-4" />
            {isStartingProcess ? "Starting..." : "Clean & Diarize"}
          </Button>
        )}

        {showRestartButton && (
          <Button
            variant="outline"
            onClick={restartProcessing}
            size="sm"
            className="gap-2"
            disabled={isRestartingProcess || isStartingProcess}
          >
            {isRestartingProcess ? "Restarting..." : "Restart processing"}
          </Button>
        )}

        {(meeting.processedStatus === "queued" || meeting.processedStatus === "running") && (
          <div className="flex items-center gap-3 w-full">
            <div className="flex flex-col gap-1 flex-1">
              <div className="flex items-center gap-2">
                <div className="h-4 w-4 rounded-full border-2 border-transparent border-t-primary border-r-primary animate-spin" />
                <span className="text-sm text-muted-foreground">
                  {meeting.processedStatus === "queued" ? "Queued..." : (meeting.processedDetail || "Processing...")}
                </span>
                {meeting.processedProgressPct && (
                  <span className="text-xs text-muted-foreground ml-auto">{meeting.processedProgressPct}%</span>
                )}
              </div>
              {meeting.processedProgressPct && (
                <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${Math.min(100, meeting.processedProgressPct)}%` }}
                  />
                </div>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={stopProcessing}
              disabled={isRestartingProcess}
              className="gap-2 text-destructive hover:text-destructive"
            >
              <X className="h-4 w-4" />
              Stop
            </Button>
          </div>
        )}

        {meeting.processedStatus === "failed" && (
          <span className="text-sm text-destructive">
            {meeting.processedError || "Processing failed."}
          </span>
        )}

        {showToggle && (
          <div className="ml-auto flex items-center gap-2">
            <Button
              size="sm"
              variant={viewMode === "original" ? "default" : "outline"}
              onClick={() => setViewMode("original")}
            >
              Original
            </Button>
            <Button
              size="sm"
              variant={viewMode === "cleaned" ? "default" : "outline"}
              onClick={() => {
                setViewMode("cleaned");
                if (processedTranscript.length === 0) {
                  void loadProcessed();
                }
              }}
            >
              Cleaned
            </Button>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-3 scrollbar-thin">
        {viewMode === "cleaned" && isLoadingProcessed && (
          <p className="text-sm text-muted-foreground">Loading cleaned transcript...</p>
        )}
        {viewMode === "cleaned" && processedLoadError && (
          <p className="text-sm text-destructive">{processedLoadError}</p>
        )}
        {activeTranscript.map((entry) => {
          const label = speakerLabelFor(entry.speaker, speakerLabelMap);
          return (
            <div key={entry.id} className="flex gap-3">
              <span
                className={`text-xs font-semibold shrink-0 px-2 py-0.5 rounded-full ${speakerBadgeColor(label)}`}
              >
                {label}
              </span>
              <p className="text-sm text-foreground leading-relaxed">{entry.text}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
