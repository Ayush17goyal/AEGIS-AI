export type VideoSource = { src: string; type: "video/webm" | "video/mp4" };
type MediaManifest = { desktop: VideoSource[]; mobile: VideoSource[] };

export function videoAllowed(
  reduced: boolean,
  connection?: { saveData?: boolean; effectiveType?: string },
) {
  return (
    !reduced &&
    !connection?.saveData &&
    !/(^|-)2g$/.test(connection?.effectiveType ?? "")
  );
}

export async function resolveHeroSource(
  mobile: boolean,
  canPlay: (type: string) => boolean,
  request: typeof fetch,
  signal: AbortSignal,
): Promise<VideoSource | null> {
  try {
    const response = await request("/videos/hero-media.json", { signal });
    if (!response.ok) return null;
    const manifest: MediaManifest = await response.json();
    const candidates = mobile ? manifest.mobile : manifest.desktop;
    if (!Array.isArray(candidates)) return null;
    for (const candidate of candidates) {
      if (
        !candidate ||
        typeof candidate.src !== "string" ||
        !/^\/videos\/aegis-hero(?:-mobile)?\.(webm|mp4)$/.test(candidate.src) ||
        !["video/webm", "video/mp4"].includes(candidate.type) ||
        !canPlay(candidate.type)
      )
        continue;
      // Refuse a desktop URL mislabeled as a mobile rendition.
      if (mobile && !candidate.src.startsWith("/videos/aegis-hero-mobile."))
        continue;
      const media = await request(candidate.src, { method: "HEAD", signal });
      if (
        media.ok &&
        media.headers.get("content-type")?.split(";")[0] === candidate.type &&
        Number(media.headers.get("content-length") ?? "1") > 0 &&
        !signal.aborted
      )
        return candidate;
    }
  } catch {
    /* Keep the original image for optional media failures. */
  }
  return null;
}
