import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import assert from 'node:assert/strict';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const browser = await chromium.launch({ channel: process.env.BROWSER_CHANNEL || 'msedge', headless: true });
const output = process.env.THEME_SCREENSHOTS || 'artifacts/theme-check';
await mkdir(output, { recursive: true });
const page = await browser.newPage();
const errors = [];
page.on('pageerror', error => errors.push(error.message));
try {
  await page.goto(process.env.THEME_URL || 'http://127.0.0.1:5173');
  await page.locator('.cinematic-landing').waitFor();
  for (const width of [1440, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const theme of ['light', 'dark']) {
      if (await page.locator('html').getAttribute('data-theme') !== theme) {
        await page.getByRole('button', { name: 'Switch to ' + theme + ' theme' }).click();
      }
      await page.reload();
      await page.locator('.cinematic-landing').waitFor();
      assert.equal(await page.locator('html').getAttribute('data-theme'), theme);
      assert.equal(await page.evaluate(() => localStorage.getItem('aegis-theme')), theme);
      await page.waitForTimeout(1800);
      // Exercise scroll-driven reveals before capturing the complete document.
      await page.locator('footer').scrollIntoViewIfNeeded();
      await page.waitForTimeout(300);
      await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Horizontal overflow at ' + width);
      await page.screenshot({ path: output + '/' + theme + '-' + width + '.png', fullPage: true });
      console.log(theme, width, await page.locator('.hero h1').evaluate(el => getComputedStyle(el).color));
      await page.getByRole('button', { name: 'Enter secure workspace' }).click();
      await page.getByRole('dialog').waitFor();
      await page.screenshot({ path: output + '/' + theme + '-login-' + width + '.png' });
      await page.getByRole('button', { name: /close/i }).click();
    }
  }
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (const width of [1440, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const theme of ['light', 'dark']) {
      if (await page.locator('html').getAttribute('data-theme') !== theme)
        await page.getByRole('button', { name: 'Switch to ' + theme + ' theme' }).click();
      await page.reload();
      await page.locator('.hero-media[data-media="poster"]').waitFor();
      await page.screenshot({ path: output + '/' + theme + '-poster-' + width + '.png', fullPage: true });
      // Contrast for shared text tokens on the opaque page surface. Image
      // compositing is checked separately in the visual screenshots.
      const ratios = await page.evaluate(() => {
        const style = getComputedStyle(document.documentElement);
        const luminance = hex => {
          const rgb = hex.trim().replace('#', '').match(/../g).map(x => parseInt(x, 16) / 255)
            .map(x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4);
          return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
        };
        const bg = luminance(style.getPropertyValue('--brand-bg'));
        return ['--text-primary', '--text-secondary', '--text-muted', '--brand-gold'].map(token => {
          const fg = luminance(style.getPropertyValue(token));
          return [token, (Math.max(bg, fg) + .05) / (Math.min(bg, fg) + .05)];
        });
      });
      for (const [token, ratio] of ratios)
        assert.ok(ratio >= 4.5, theme + ' ' + token + ' contrast: ' + ratio);
    }
  }
  assert.deepEqual(errors, []);
  console.log('PASS: both themes, four widths, reload persistence, dialogs, video/poster paths, text-token contrast, no horizontal overflow or JS errors.');
} finally { await browser.close(); }
