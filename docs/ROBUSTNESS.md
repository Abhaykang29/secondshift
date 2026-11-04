# Robustness sweep — odd videos through the real path (2026-11-03)

Every variant below went through the **real upload → scan path**
(POST /checkups → POST /captures → POST /scan) against the **live
Meta API**, one checklist (falls_older_adults) per scan to bound
cost. Sources: `test_1.mp4` (55s apartment walkthrough) and the
4896 kitchen clip (24s, 120fps, vertical), re-encoded with ffmpeg.
Raw results: `data/triage/robustness_results.json` (local data).

| Variant | Upload | Scan | Keyframes | Findings | What the user sees |
|---|---|---|---|---|---|
| HEVC .mov (v01) | 200 | 200 | 80 | 6 hazards, 1 can't-tell | Normal report |
| H.264 .mp4 (v02) | 200 | 200 | 80 | 4 hazards, 10 can't-tell | Normal report |
| 4K upscale (v03) | 200 | 200 | 80 | 6 hazards, 12 can't-tell | Normal report |
| 720p (v04) | 200 | 200 | 80 | 6 hazards, 12 can't-tell | Normal report |
| 30fps (v05) | 200 | 200 | 16 | 1 hazard, 2 can't-tell | Normal report |
| 60fps (v06) | 200 | 200 | 16 | 1 hazard, 15 can't-tell | Normal report |
| 120fps (v07) | 200 | 200 | 16 | 1 hazard, 13 can't-tell | Normal report |
| 240fps (v08) | 200 | 200 | 16 | 1 hazard, 19 can't-tell | Normal report |
| Vertical 9:16 (v09) | 200 | 200 | 79 | 1 hazard, 13 can't-tell | Normal report |
| 8 seconds (v10) | 200 | 200 | 16 | 1 hazard, 5 can't-tell | Normal report — short is fine |
| 4.6 minutes (v11) | 200 | 200 | 80 | 6 hazards, 9 can't-tell | Normal report — under the 6-minute cap, so it scans |
| Very dark (v12) | 200 | 200 | 49 | 1 hazard, 16 can't-tell | Report leans on can't-tell: dark frames are rejected, the ~2s coverage fill keeps the usable ones |
| Very shaky (v13) | 200 | 200 | 16 | 1 hazard, 12 can't-tell | Normal report; blur costs keyframes, can't-tell grows |
| No audio (v14) | 200 | 200 | 80 | 5 hazards, 14 can't-tell | Normal report — narration is optional |
| Truncated file (v15) | **500 → fixed** | — | — | — | See below |
| Non-video renamed .mp4 (v16) | **500 → fixed** | — | — | — | See below |

## The two crashes, and the fix

As swept, v15 and v16 returned **500 Internal Server Error**: ffprobe
failures (`CalledProcessError`, missing video stream) escaped
`probe_video` uncaught. Fixed the same day:

- `capture/probe.py` now raises a typed `CaptureUnreadable` with a
  plain message for any file ffprobe cannot read as a video.
- The upload route maps it to **422**: *"We couldn't read that file
  as a video. It may be damaged or not a video at all — please
  upload a video recorded on a phone or camera (MP4 or MOV) and try
  again."*
- Verified after the fix against the same two files: both return
  422 with that message.
- Regression tests: `test_probe_rejects_non_video_bytes`,
  `test_probe_rejects_truncated_video`,
  `test_upload_of_garbage_file_is_a_plain_422` (tests/test_capture.py).

## Notes and limits

- **Over-long videos**: the cap is 6 minutes
  (`MAX_CAPTURE_MINUTES`). No variant exceeded it (v11 is 4.6 min),
  so the over-cap path was not exercised live; it is covered by
  `test_probe_rejects_over_long_video` and returns 422 with
  *"This video is N minutes. Please keep it under 6 minutes and
  try again."*
- **Frame rate doesn't change sampling**: keyframes are sampled at
  2fps regardless of source fps, so the 30–240fps variants behave
  alike (16 keyframes from the 24s clip).
- **Person blur**: during v11, SAM person segmentation failed on 3
  of ~550 frames; the failures are logged and the scan continues —
  a failed blur never crashes a scan.
- Finding counts vary between variants of the same scene (4–6
  hazards for the test_1 encodes). That is the measured run-to-run
  variance of the vision pipeline, not an encoding effect we could
  isolate at this sample size; the consistency numbers live in
  `docs/LIVE_VERIFICATION.md`.
