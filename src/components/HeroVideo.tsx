import { useEffect, useRef, useState } from "react";

import { resolveHeroSource, videoAllowed, type VideoSource } from "./heroMedia";

/** Optional real video over the original portrait. Never mounts missing media. */
export function HeroVideo({
  motion,
  allowReducedMotion = false,
}: {
  motion: boolean;
  allowReducedMotion?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [source, setSource] = useState<VideoSource | null>(null);
  const [visible, setVisible] = useState(false);
  const [failed, setFailed] = useState(false);
  const [reduced, setReduced] = useState(
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [mobile, setMobile] = useState(
    () => window.matchMedia("(max-width: 760px)").matches,
  );

  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const breakpoint = window.matchMedia("(max-width: 760px)");
    const update = () => {
      setReduced(preference.matches);
      setMobile(breakpoint.matches);
    };
    preference.addEventListener("change", update);
    breakpoint.addEventListener("change", update);
    return () => {
      preference.removeEventListener("change", update);
      breakpoint.removeEventListener("change", update);
    };
  }, []);

  useEffect(() => {
    setSource(null);
    setVisible(false);
    setFailed(false);
    const connection = (
      navigator as Navigator & {
        connection?: { saveData?: boolean; effectiveType?: string };
      }
    ).connection;
    if (!videoAllowed(reduced && !allowReducedMotion, connection)) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 6000);
    async function discover() {
      const probe = document.createElement("video");
      const selected = await resolveHeroSource(
        mobile,
        (type) => Boolean(probe.canPlayType(type)),
        fetch,
        controller.signal,
      );
      if (!controller.signal.aborted) setSource(selected);
      window.clearTimeout(timer);
    }
    void discover();
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [mobile, reduced, allowReducedMotion]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    let active = true;
    const syncPlayback = () => {
      if (!motion || (reduced && !allowReducedMotion) || document.hidden) {
        video.pause();
        return;
      }
      video.muted = true;
      void video.play().catch((error) => {
        if (!active || error?.name === "AbortError") return;
        setFailed(true);
        setVisible(false);
      });
    };
    syncPlayback();
    document.addEventListener("visibilitychange", syncPlayback);
    return () => {
      active = false;
      document.removeEventListener("visibilitychange", syncPlayback);
      video.pause();
    };
  }, [source, motion, reduced, allowReducedMotion, failed]);

  return (
    <div
      className={`scene-image hero-media${source && !failed && visible ? " has-video" : ""}`}
      aria-hidden="true"
      data-media={source && !failed ? "video" : "poster"}
    >
      {source && !failed && (!reduced || allowReducedMotion) && (
        <>
          <video
            key={source.src}
            ref={videoRef}
            className={`hero-video${visible ? " is-ready" : ""}`}
            autoPlay={motion}
            muted
            loop
            playsInline
            preload="metadata"
            poster={mobile ? "/aegis-hero-mobile.webp" : "/aegis-hero.webp"}
            disablePictureInPicture
            tabIndex={-1}
            onPlaying={() => setVisible(true)}
            onError={() => {
              setFailed(true);
              setVisible(false);
            }}
          >
            <source src={source.src} type={source.type} />
          </video>
          <div className="hero-video-overlay" />
        </>
      )}
    </div>
  );
}
