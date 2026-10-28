import en from "../i18n/en.json";

/** Every page footer carries the screening disclaimer (spec section 13). */
export default function Footer() {
  return (
    <footer className="mx-auto max-w-2xl p-6 text-sm opacity-80">
      {en.screening_footer} {en.footer_disclaimer}
    </footer>
  );
}
