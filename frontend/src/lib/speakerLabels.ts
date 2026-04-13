const SPEAKER_TEXT_COLORS = ["text-speaker-1", "text-speaker-2", "text-speaker-3"] as const;
const SPEAKER_BADGE_COLORS = [
  "text-speaker-1 bg-speaker-1/10",
  "text-speaker-2 bg-speaker-2/10",
  "text-speaker-3 bg-speaker-3/10",
] as const;

function normalizeSpeakerKey(rawSpeaker: string): string {
  return (rawSpeaker || "speaker").trim().toLowerCase();
}

function extractSpeakerNumber(rawSpeaker: string): number | null {
  const match = rawSpeaker.match(/speaker[\s_-]*(\d+)/i);
  if (!match) return null;
  const parsed = Number.parseInt(match[1], 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function speakerIndexFromLabel(label: string): number {
  const match = label.match(/speaker\s+(\d+)/i);
  const parsed = match ? Number.parseInt(match[1], 10) : 1;
  return Math.max(1, Number.isFinite(parsed) ? parsed : 1) - 1;
}

export function buildSpeakerLabelMap(rawSpeakers: string[]): Map<string, string> {
  const keys: string[] = [];
  const numericHints: number[] = [];

  for (const rawSpeaker of rawSpeakers) {
    const key = normalizeSpeakerKey(rawSpeaker);
    if (keys.includes(key)) {
      continue;
    }
    keys.push(key);
    const numberHint = extractSpeakerNumber(rawSpeaker);
    if (numberHint !== null) {
      numericHints.push(numberHint);
    }
  }

  const hasZeroBasedHints = numericHints.includes(0);
  const map = new Map<string, string>();
  const usedNumbers = new Set<number>();
  let nextSpeakerNumber = 1;

  for (const key of keys) {
    const numberHint = extractSpeakerNumber(key);
    if (numberHint === null) {
      continue;
    }
    const resolved = Math.max(1, hasZeroBasedHints ? numberHint + 1 : numberHint);
    if (usedNumbers.has(resolved)) {
      continue;
    }
    usedNumbers.add(resolved);
    map.set(key, `Speaker ${resolved}`);
    nextSpeakerNumber = Math.max(nextSpeakerNumber, resolved + 1);
  }

  for (const key of keys) {
    if (map.has(key)) {
      continue;
    }
    while (usedNumbers.has(nextSpeakerNumber)) {
      nextSpeakerNumber += 1;
    }
    usedNumbers.add(nextSpeakerNumber);
    map.set(key, `Speaker ${nextSpeakerNumber}`);
    nextSpeakerNumber += 1;
  }

  return map;
}

export function speakerLabelFor(rawSpeaker: string, map: Map<string, string>): string {
  const key = normalizeSpeakerKey(rawSpeaker);
  const existing = map.get(key);
  if (existing) {
    return existing;
  }
  const fallbackNumber = map.size + 1;
  const fallback = `Speaker ${fallbackNumber}`;
  map.set(key, fallback);
  return fallback;
}

export function speakerTextColor(label: string): string {
  const idx = speakerIndexFromLabel(label) % SPEAKER_TEXT_COLORS.length;
  return SPEAKER_TEXT_COLORS[idx];
}

export function speakerBadgeColor(label: string): string {
  const idx = speakerIndexFromLabel(label) % SPEAKER_BADGE_COLORS.length;
  return SPEAKER_BADGE_COLORS[idx];
}
