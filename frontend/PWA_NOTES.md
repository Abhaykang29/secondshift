# SecondShift PWA notes

SecondShift ships as an installable, mobile-first web app (PWA):
`public/manifest.webmanifest` + `public/sw.js` (app shell only — the
service worker never caches `/api/*` responses, videos or reports).
The service worker is registered only in production builds
(`import.meta.env.PROD` in `src/main.tsx`).

## Run it over HTTPS (required for iPhone camera + install)

iPhone Safari only allows `getUserMedia` and Add-to-Home-Screen on
HTTPS (or localhost). Options:

1. **Local HTTPS (repo root):** `make dev-https` — serves the app with
   a self-signed local certificate for LAN testing. Accept the
   certificate warning on the phone once.
2. **Tunnel (real certificate, easiest for a demo phone):**
   - `npx localtunnel --port 5173` (free, gives an https URL), or
   - `ngrok http 5173` (needs a free ngrok account).
   Run the backend on :8000 and the frontend dev server on :5173 as
   usual (`make dev`); the tunnel forwards the frontend, and Vite
   proxies `/api` to the backend. For a production build
   (`npm run build` + `vite preview`), tunnel the preview port instead.

## Add to Home Screen (iPhone)

1. Open the HTTPS URL in **Safari** (not Chrome — iOS install is
   Safari-only).
2. Tap the **Share** button.
3. Tap **Add to Home Screen**, keep the name "SecondShift", tap **Add**.
4. Launch from the home-screen icon: it opens full-screen
   (`display: standalone`), with the bottom tab bar
   (Check / Live / Homes / Learn).

Android/desktop Chrome: use "Install app" from the browser menu; the
same manifest and icons apply (a maskable 512 icon is included).

## Icons

`public/icons/` — generated with Python PIL (white house + check on
the deep-green theme colour `#1f3d2b`): 192, 512, 512 maskable, and a
180px apple-touch-icon. No external assets.
