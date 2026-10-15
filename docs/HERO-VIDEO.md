# Cinematic hero video integration

The supplied `agenx_person_zoomed.mp4` is now integrated. Its original 1918×876, 30 FPS footage includes recorded interface text, so the implementation extracts the clean 920×860 character region and softly masks the edges. The portrait is displayed about 25% smaller and positioned farther right for balanced framing on desktop, with separate tablet and mobile sizing. The real headline and security UI remain separate, functional HTML.

The audio track is removed. A 5.9-second excerpt plays forward and then in reverse to create an 11.8-second loop with matching start/end poses. Desktop WebM and H.264 MP4 plus smaller 640-pixel mobile renditions are registered in `public/videos/hero-media.json`. When actual playback begins, the static character underneath is removed to prevent a ghosted second face. The image remains the loading/error fallback.

## Supply the final video

Use `public/aegis-hero.png` as the image-to-video reference. Preserve the silver-haired woman, black outfit, amber visor, center-right positioning, dark copper smoke, and fixed camera. Request subtle natural face/head movement, hair movement, visor lighting changes, and drifting smoke. No talking, exaggerated expressions, rapid movement, or obvious loop seam.

Place one or both desktop formats here:

- `public/videos/aegis-hero.webm` (VP9, preferred)
- `public/videos/aegis-hero.mp4` (H.264, yuv420p, fast-start fallback)

Optional mobile renditions:

- `public/videos/aegis-hero-mobile.webm`
- `public/videos/aegis-hero-mobile.mp4`

Then run:

```powershell
node scripts/configure-hero-video.mjs
npm run build
```

The script registers only files that exist and contain bytes. No missing URL is inserted into the video element. The browser also checks the selected file's MIME type before mounting it. Reload the preview after replacing/configuring assets; rebuild static deployments. Nginx/Vite should serve MP4 as `video/mp4` and WebM as `video/webm`.

## Recommended export

8–15 seconds, 24/30 FPS, seamless loop. Prefer 1920×1080 or wider. Compose the subject center-right and leave negative space for the left headline and right security overlays. Keep the reference's camera framing throughout the clip. Aim for a desktop rendition below 5 MB and mobile below 2 MB. Avoid audio tracks entirely.

For an existing generated master file (these commands encode supplied footage, they do not generate character motion):

```powershell
ffmpeg -i character-master.mov -an -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=24" -c:v libx264 -crf 24 -preset slow -pix_fmt yuv420p -movflags +faststart public/videos/aegis-hero.mp4
ffmpeg -i character-master.mov -an -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=24" -c:v libvpx-vp9 -crf 34 -b:v 0 public/videos/aegis-hero.webm
ffmpeg -i character-master.mov -an -vf "scale=960:540:force_original_aspect_ratio=increase,crop=960:540,fps=24" -c:v libx264 -crf 27 -pix_fmt yuv420p -movflags +faststart public/videos/aegis-hero-mobile.mp4
```

A different aspect ratio may need subject-aware crop tuning in `src/landing.css`. The original still is 3:2; a 16:9 master should preserve the subject's screen position after the background cover crop, especially on mobile.

## Behavior

- Reusable `src/components/HeroVideo.tsx` renders within the existing page-level scene. Content and navigation stay above it.
- One supported source is chosen: WebM first, then MP4. Only the chosen video is downloaded.
- Mobile chooses its own rendition. With no mobile video, it keeps the lightweight mobile portrait; it never falls back to downloading the full desktop clip.
- Reduced-motion preference, Save-Data, and slow 2G connections retain the static image without requesting video content. A reduced-motion user can explicitly select the existing Play control to opt into video playback; decorative CSS motion remains disabled. Save-Data and slow 2G still retain the poster.
- Autoplay is muted, inline, looping, and has no visible controls. Existing pause/play button controls the video.
- Poster remains visible while loading. Invalid MIME, missing assets, decoder failure, or blocked autoplay returns to the original portrait.
- Background tabs pause playback. Returning to the page resumes if motion is enabled.
- The portrait fallback and gradients retain the current composition. No character video is claimed while the manifest is empty.

## Validation

Run `node --test scripts/hero-media.test.mjs` for the 11 source-selection and fallback tests. They cover missing files, invalid MIME, supported-format preference, mobile selection, cancellation, invalid URLs, and data-saving/reduced-motion rules. They do not generate footage or prove playback of a final character clip.

The supplied footage has been checked in the running page: desktop and mobile WebM playback, muted looping, advancing playback time, and pause holding the same timestamp. Reduced-motion mode still starts with the original image unless Play is explicitly selected. The processed forward/reverse loop has matching start/end poses. The original page links and workspace CTA remain separate from the video and functional.

