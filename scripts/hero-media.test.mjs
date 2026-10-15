import test from "node:test";
import assert from "node:assert/strict";
import {
  resolveHeroSource,
  videoAllowed,
} from "../src/components/heroMedia.ts";

const webm = { src: "/videos/aegis-hero.webm", type: "video/webm" };
const mp4 = { src: "/videos/aegis-hero.mp4", type: "video/mp4" };
const mobile = { src: "/videos/aegis-hero-mobile.mp4", type: "video/mp4" };
function fixture(manifest, responses = {}) {
  const calls = [];
  const request = async (url, options = {}) => {
    calls.push({ url, method: options.method ?? "GET" });
    if (url === "/videos/hero-media.json")
      return new Response(JSON.stringify(manifest), {
        headers: { "content-type": "application/json" },
      });
    return responses[url] ?? new Response("", { status: 404 });
  };
  return { request, calls };
}
const valid = (type) =>
  new Response("test bytes", {
    headers: { "content-type": type, "content-length": "10" },
  });
const resolve = (
  f,
  mobile = false,
  supported = () => true,
  signal = new AbortController().signal,
) => resolveHeroSource(mobile, supported, f.request, signal);
test("no supplied assets => no video URL requested", async () => {
  const f = fixture({ desktop: [], mobile: [] });
  assert.equal(await resolve(f), null);
  assert.equal(f.calls.length, 1);
});
test("choose one WebM source without loading MP4", async () => {
  const f = fixture(
    { desktop: [webm, mp4], mobile: [] },
    { [webm.src]: valid(webm.type) },
  );
  assert.deepEqual(await resolve(f), webm);
  assert.equal(f.calls.length, 2);
});
test("unsupported WebM selects MP4", async () => {
  const f = fixture(
    { desktop: [webm, mp4], mobile: [] },
    { [mp4.src]: valid(mp4.type) },
  );
  assert.deepEqual(
    await resolve(f, false, (type) => type === "video/mp4"),
    mp4,
  );
  assert.ok(!f.calls.some((c) => c.url === webm.src));
});
test("mobile without a rendition never requests desktop video", async () => {
  const f = fixture({ desktop: [webm], mobile: [] });
  assert.equal(await resolve(f, true), null);
  assert.equal(f.calls.length, 1);
});
test("mobile selects only its optimized rendition", async () => {
  const f = fixture(
    { desktop: [webm], mobile: [mobile] },
    { [mobile.src]: valid(mobile.type) },
  );
  assert.deepEqual(await resolve(f, true), mobile);
});
test("mislabeled desktop source in mobile manifest is refused", async () => {
  const f = fixture({ desktop: [], mobile: [mp4] });
  assert.equal(await resolve(f, true), null);
  assert.equal(f.calls.length, 1);
});
test("SPA HTML response is refused as media", async () => {
  const f = fixture(
    { desktop: [webm], mobile: [] },
    {
      [webm.src]: new Response("<html/>", {
        headers: { "content-type": "text/html" },
      }),
    },
  );
  assert.equal(await resolve(f), null);
});
test("missing video returns poster instead of mounting a broken source", async () => {
  const f = fixture({ desktop: [mp4], mobile: [] });
  assert.equal(await resolve(f), null);
});
test("empty file and aborted discovery never select a video", async () => {
  const f = fixture(
    { desktop: [mp4], mobile: [] },
    {
      [mp4.src]: new Response("", {
        headers: { "content-type": mp4.type, "content-length": "0" },
      }),
    },
  );
  assert.equal(await resolve(f), null);
  const c = new AbortController();
  c.abort();
  assert.equal(await resolve(f, false, () => true, c.signal), null);
});
test("external or unknown filenames are not fetched", async () => {
  const f = fixture({
    desktop: [{ src: "https://example.test/unrelated.mp4", type: "video/mp4" }],
    mobile: [],
  });
  assert.equal(await resolve(f), null);
  assert.equal(f.calls.length, 1);
});
test("reduced motion, Save-Data and 2G prevent video loading", () => {
  assert.equal(videoAllowed(true), false);
  assert.equal(videoAllowed(false, { saveData: true }), false);
  assert.equal(videoAllowed(false, { effectiveType: "slow-2g" }), false);
  assert.equal(videoAllowed(false, { effectiveType: "4g" }), true);
});
