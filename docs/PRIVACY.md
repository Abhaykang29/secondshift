# Privacy

Spec section 14, enforced in code - summary:

1. Consent before capture; nobody filmed in a bathroom or undressed.
2. Data minimization: raw video deleted after processing unless `keep_raw_video`; keyframes kept `retention_days` (default 30) for re-checks; Watch frames in memory only, only the ROI is analyzed or sent; event thumbnails are ROI crops with people blurred, deleted after 7 days.
3. People blurring on every frame saved to disk (SAM "person" mask, Gaussian blur); fallback: blur everything outside the ROI/hazard region.
4. Room guard: bathrooms always refused for Watch; bedrooms require an explicit resident-consent toggle.
5. No identity, ever: no face recognition, no re-identification, no "who" rules, no tracking across rooms.
6. No medical claims; narration facts drop health details.
7. Honest uncertainty: CANNOT TELL is a first-class, visible result.
8. Meta data terms: Standard tier only for real images/video/audio. "Occasional snapshots are sent to Meta's AI models to check them. On the Standard tier, Meta says prompts and outputs are not used to train its models. We don't claim zero retention."
9. Security: never log keys, RTSP URLs with credentials, or media. Local-network-only camera use is recommended (cameras can be blocked from the internet at the router).
10. This is consented, in-home safety screening of objects and spaces - never a tool to monitor people without their knowledge.
