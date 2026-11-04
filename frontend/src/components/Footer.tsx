import en from "../i18n/en.json";

/** Footer (redesign spec 4.4): 13px, text-3, centered, one sentence. */
export default function Footer() {
  return (
    <footer className="mx-auto mt-8 max-w-2xl p-6 text-center text-[13px] text-text-3">
      {en.footer_disclaimer}
    </footer>
  );
}
