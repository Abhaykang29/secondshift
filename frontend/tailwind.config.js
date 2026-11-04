/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        "surface-3": "var(--surface-3)",
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        text: "var(--text)",
        "text-2": "var(--text-2)",
        "text-3": "var(--text-3)",
        "text-inverse": "var(--text-inverse)",
        accent: "var(--accent)",
        "accent-hover": "var(--accent-hover)",
        "accent-bg": "var(--accent-bg)",
        ok: "var(--ok)",
        "ok-bg": "var(--ok-bg)",
        warn: "var(--warn)",
        "warn-bg": "var(--warn-bg)",
        bad: "var(--bad)",
        "bad-bg": "var(--bad-bg)",
        unk: "var(--unk)",
        "unk-bg": "var(--unk-bg)",
      },
      borderRadius: {
        card: "var(--r-card)",
        btn: "var(--r-btn)",
        chip: "var(--r-chip)",
        tile: "var(--r-tile)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        menu: "var(--shadow-menu)",
      },
    },
  },
  plugins: [],
};
