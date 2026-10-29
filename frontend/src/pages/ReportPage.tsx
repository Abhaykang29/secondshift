import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Report } from "../api/types";
import BeforeAfter from "../components/BeforeAfter";
import HazardCard from "../components/HazardCard";
import en from "../i18n/en.json";

/**
 * The report page (spec 5.1 step 6) - the money screen: summary,
 * fix-these-first, hazard cards with SAM overlays, routine insights,
 * fix cards, after-visualizations, needs-a-human, couldn't-check, share.
 */
export default function ReportPage() {
  const { id = "" } = useParams();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [shareUrl, setShareUrl] = useState("");

  useEffect(() => {
    api.report(id).then(setReport).catch(() => setError("No report yet - run a scan first."));
    api.share(id).then((s) => setShareUrl(s.whatsapp_url)).catch(() => setShareUrl(""));
  }, [id]);

  const byId = useMemo(
    () => new Map((report?.hazards ?? []).map((h) => [h.id, h])),
    [report],
  );
  if (error) return <main className="mx-auto max-w-2xl p-6"><p role="alert">{error}</p></main>;
  if (!report) return <main className="mx-auto max-w-2xl p-6"><p>Loading the report...</p></main>;

  const confirmed = report.hazards
    .filter((h) => h.verification === "confirmed")
    .sort((a, b) => a.pack_id.localeCompare(b.pack_id) || (a.rank ?? 99) - (b.rank ?? 99));
  const needsHuman = report.hazards.filter((h) => h.verification === "needs_human");
  const vizByHazard = new Map(report.visualizations.map((v) => [v.hazard_id, v]));

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-3xl font-semibold">Home check-up report</h1>
      <p className="mt-3 text-lg">{report.summary}</p>

      <section aria-label="Fix these first" className="mt-6 rounded bg-amber-50 p-4">
        <h2 className="text-xl font-semibold">Fix these {report.fix_first.length} first</h2>
        <ol className="mt-2 list-decimal pl-6">
          {report.fix_first.map((hid) => (
            <li key={hid}>{byId.get(hid)?.title ?? hid}</li>
          ))}
        </ol>
      </section>

      <section aria-label="Hazards">
        {confirmed.map((h, i) => (
          <div key={h.id}>
            {(report.pack_ids.length > 1 &&
              (i === 0 || confirmed[i - 1].pack_id !== h.pack_id)) && (
              <h3 className="mt-5 text-lg font-semibold">
                Checklist: {h.pack_id}
                {h.pack_tags && h.pack_tags.length > 1
                  ? ` (also in ${h.pack_tags.filter((x) => x !== h.pack_id).join(", ")})`
                  : ""}
              </h3>
            )}
            <HazardCard hazard={h} />
            {vizByHazard.has(h.id) && (
              <BeforeAfter
                title={h.title}
                beforeUrl={api.imageUrl(id, `before-${h.id}.png`)}
                afterUrl={api.imageUrl(id, vizByHazard.get(h.id)?.image_path ?? "")}
              />
            )}
          </div>
        ))}
      </section>

      {report.routine_insights.length > 0 && (
        <section aria-label="Routine insights" className="mt-8">
          <h2 className="text-xl font-semibold">From the routine clip</h2>
          {report.routine_insights.map((insight) => (
            <p key={insight.id} className="mt-2 rounded bg-blue-50 p-3">{insight.summary}</p>
          ))}
        </section>
      )}

      <section aria-label="Fix plan" className="mt-8">
        <h2 className="text-xl font-semibold">Fix plan</h2>
        {report.fixes.map((card) => (
          <article key={card.id} className="mt-3 rounded border p-4">
            <h3 className="font-medium">{card.chosen.title}</h3>
            <p className="text-sm opacity-80">
              {card.chosen.difficulty} - cost estimate: {card.chosen.cost_estimate}
            </p>
            <ol className="mt-2 list-decimal pl-6">
              {card.plain_language_steps.map((s) => <li key={s}>{s}</li>)}
            </ol>
            {card.alternatives.length > 0 && (
              <p className="mt-2 text-sm">Also possible: {card.alternatives.map((a) => a.title).join("; ")}</p>
            )}
          </article>
        ))}
      </section>

      {needsHuman.length > 0 && (
        <section aria-label="Needs a human look" className="mt-8">
          <h2 className="text-xl font-semibold">Needs a human look</h2>
          {needsHuman.map((h) => <HazardCard key={h.id} hazard={h} />)}
        </section>
      )}

      {report.cannot_assess.length > 0 && (
        <section aria-label="Couldn't check" className="mt-8">
          <h2 className="text-xl font-semibold">Couldn't check</h2>
          {report.cannot_assess.map((c) => (
            <p key={c.area} className="mt-2">
              {en.cannot_tell.replace("<reason>", `${c.area}: ${c.detail}`)}
            </p>
          ))}
        </section>
      )}

      <div className="mt-8 flex gap-3">
        {shareUrl && (
          <a href={shareUrl} target="_blank" rel="noreferrer" className="rounded bg-green-700 px-4 py-3 text-white">
            Share on WhatsApp
          </a>
        )}
        <button type="button" onClick={() => window.print()} className="rounded border px-4 py-3">
          Print the report
        </button>
      </div>
      <p className="mt-4 text-sm opacity-80">{report.disclaimer}</p>
    </main>
  );
}
