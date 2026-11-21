// Drive the sim in headless Chromium and print its final report as JSON.
// usage: node scenario.mjs <url> <screenshot.png> [timeout_s]
import { chromium } from "playwright";

const [url, shot, timeoutS = "180"] = process.argv.slice(2);
const browser = await chromium.launch({
  args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
const page = await browser.newPage({ viewport: { width: 1100, height: 560 } });
page.on("pageerror", (e) => console.error("pageerror:", e.message));
page.on("console", (m) => m.type() === "error" && console.error("console:", m.text()));
await page.goto(url);
try {
  await page.waitForFunction(() => document.title === "DONE" || window.__error, null, { timeout: Number(timeoutS) * 1000, polling: 500 });
} catch (e) {
  console.error("timeout waiting for scenario");
}
await page.screenshot({ path: shot });
const out = await page.evaluate(() => window.__report ?? { error: window.__error ?? "no report" });
console.log(JSON.stringify(out));
await browser.close();
