import { readdir, stat, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const directory = path.join(root, "public", "videos");
const files = await readdir(directory);
const manifest = { desktop: [], mobile: [] };
for (const rendition of ["desktop", "mobile"]) {
  const name = rendition === "mobile" ? "aegis-hero-mobile" : "aegis-hero";
  for (const extension of ["webm", "mp4"]) {
    const filename = `${name}.${extension}`;
    if (!files.includes(filename)) continue;
    const info = await stat(path.join(directory, filename));
    if (!info.isFile() || info.size === 0)
      throw new Error(`Empty media file: ${filename}`);
    manifest[rendition].push({
      src: `/videos/${filename}`,
      type: `video/${extension}`,
    });
  }
}
await writeFile(
  path.join(directory, "hero-media.json"),
  JSON.stringify(manifest, null, 2) + "\n",
);
console.log(
  `Hero media configured: ${manifest.desktop.length} desktop source(s), ${manifest.mobile.length} mobile source(s).`,
);
if (!manifest.desktop.length)
  console.log(
    "No character video supplied. The original portrait remains the visible fallback.",
  );
