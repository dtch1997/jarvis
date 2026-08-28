import { chromium } from 'playwright';

const dir = '/tmp/claude-2038/-mnt-nw-home-d-tan-jarvis-monorepo-jarvis-os/0089fa65-26e0-498e-9489-9fd4a2b5a77f/scratchpad';
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
await page.goto('file://' + dir + '/rl-regime-talk-print.html', { waitUntil: 'networkidle' });
await page.emulateMedia({ media: 'print', colorScheme: 'light' });
await page.pdf({
  path: dir + '/will-alignment-techniques-scale-to-rl.pdf',
  width: '338.67mm',
  height: '190.5mm',
  printBackground: true,
});
await browser.close();
console.log('pdf written');
