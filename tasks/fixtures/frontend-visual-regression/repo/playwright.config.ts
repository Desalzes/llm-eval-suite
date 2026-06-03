import fs from "node:fs";
import { defineConfig, type PlaywrightTestConfig } from "@playwright/test";

const chromeCandidates =
  process.platform === "win32"
    ? [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
      ]
    : [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser"
      ];

const hasSystemChrome = chromeCandidates.some((candidate) =>
  fs.existsSync(candidate)
);

const browserUse: PlaywrightTestConfig["use"] = hasSystemChrome
  ? { channel: "chrome" }
  : {};

export default defineConfig({
  testDir: "./tests/visual",
  fullyParallel: false,
  reporter: "line",
  timeout: 30_000,
  use: {
    ...browserUse,
    baseURL: "http://127.0.0.1:4173",
    screenshot: "off",
    trace: "off"
  },
  webServer: {
    command: "node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 4173",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
    timeout: 120_000
  }
});
