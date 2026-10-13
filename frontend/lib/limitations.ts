// User-facing limitations of the AI (TRAN-02). Keep in step with
// governance/system-limitations.yaml and backend/app/services/explain.py.

export const LIMITATIONS: string[] = [
  "A similarity score is an estimate, not an identification.",
  "Accuracy can be lower for some ages, skin tones, poses, lighting and image quality.",
  "Low-quality, small, blurred, occluded or side-on faces make errors more likely.",
  "Look-alikes and close relatives can score highly.",
  "In a group photo the largest face is used as the reference.",
];

export const BAND_LABEL: Record<string, { label: string; tone: string }> = {
  low: { label: "Low confidence - the system is uncertain", tone: "text-amber-300" },
  medium: { label: "Medium confidence", tone: "text-slate-300" },
  high: { label: "High similarity - still not proof", tone: "text-emerald-300" },
  human: { label: "Added by a reviewer", tone: "text-sky-300" },
};

export function bandFor(score: number | null, threshold: number): keyof typeof BAND_LABEL {
  if (score == null) return "human";
  const margin = score - threshold;
  return margin < 0.1 ? "low" : margin < 0.25 ? "medium" : "high";
}
