export type BoundingBox = { x: number; y: number; w: number; h: number };
export type FaceRecord = {
  face_id: string;
  photo_id: string;
  bbox: BoundingBox;
  det_score: number;
  quality: number;
};
export type UploadResponse = {
  photo_id: string;
  url: string;
  faces: FaceRecord[];
  message: string;
};
export type SearchMatch = {
  photo_id: string;
  face_id: string;
  url: string;
  score: number;
  bbox: BoundingBox;
};
export type SearchResponse = {
  query_faces: number;
  matches: SearchMatch[];
};
export type Health = {
  status: string;
  detector: string;
  storage: string;
  vector_store: string;
  indexed_faces: number;
};

export async function uploadPhoto(file: File): Promise<UploadResponse> {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch("/api/upload", { method: "POST", body: fd });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function searchPhoto(
  file: File,
  { limit = 24, threshold = 0.35 }: { limit?: number; threshold?: number } = {}
): Promise<SearchResponse> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("limit", String(limit));
  fd.append("threshold", String(threshold));
  const r = await fetch("/api/search", { method: "POST", body: fd });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getHealth(): Promise<Health> {
  const r = await fetch("/api/health", { cache: "no-store" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getGallery(): Promise<{
  count: number;
  items: { photo_id: string; url: string; filename?: string; quality?: number }[];
}> {
  const r = await fetch("/api/gallery", { cache: "no-store" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export function photoUrl(photo_id: string): string {
  return `/photos/${photo_id}`;
}
