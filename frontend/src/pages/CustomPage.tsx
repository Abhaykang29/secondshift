import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { CustomChecklistResponse } from "../api/extra";

/** Bring your own checklist (Pass 3 P4): type 3-10 plain-English lines,
 * Spark compiles each into a checkable item or refuses it with a reason.
 * Drafts are labelled and excluded from eval. */

export default function CustomPage() {
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<CustomChecklistResponse | null>(null);

  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);

  async function compile() {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const compiled = await api.compileCustom(lines);
      setResult(compiled);
    } catch (err) {
      setError(
        "Those lines could not be compiled. Lines that need touch, tightness, " +
          "smell, sound or a working test can't be checked from video - try describing " +
          "what a camera can see.",
      );
      void err;
    } finally {
      setBusy(false);
    }
  }

  function useChecklist() {
    if (!result) return;
    sessionStorage.setItem("pack_selection", JSON.stringify([result.checklist_id]));
    navigate("/checkup/new");
  }

  return (
    <main className="mx-auto max-w-md p-4 pb-28">
      <h1 className="text-2xl font-bold">Your own checklist</h1>
      <p className="mt-2 opacity-80">
        Type what you want checked, one line each (3 to 10 lines). Each line is
        turned into something a camera can verify - or refused, with the reason.
      </p>
      <p className="mt-2 rounded bg-amber-100 p-2 text-sm font-medium text-amber-900">
        Custom checklist - not reviewed by an expert
      </p>
      <textarea
        className="mt-4 min-h-44 w-full rounded border-2 border-stone-300 p-3 text-lg"
        placeholder={
          "loose cords across the walkway\nboxes stacked above shoulder height\nfire extinguisher mounted by the exit"
        }
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <p className="mt-1 text-sm opacity-70">{lines.length} line(s) - needs 3 to 10</p>
      <button
        type="button"
        disabled={busy || lines.length < 3 || lines.length > 10}
        onClick={compile}
        className="mt-3 min-h-12 w-full rounded bg-emerald-900 px-4 py-3 font-semibold text-white disabled:opacity-40"
      >
        {busy ? "Compiling..." : "Compile my checklist"}
      </button>
      {error && (
        <p role="alert" className="mt-3 rounded bg-red-100 p-3 text-red-900">
          {error}
        </p>
      )}
      {result && (
        <section className="mt-5">
          <h2 className="text-lg font-semibold">What will be checked</h2>
          <ul className="mt-2 space-y-2">
            {result.items.map((item) => (
              <li key={item.id} className="rounded border-2 border-emerald-800/40 bg-emerald-50 p-3">
                <span className="font-medium">{item.title}</span>
                <span className="block text-sm opacity-70">
                  looks for: {item.sam_prompts.join(", ")}
                  {item.thin_object ? " · close-up crops for thin objects" : ""}
                </span>
              </li>
            ))}
          </ul>
          {result.refusals.length > 0 && (
            <>
              <h2 className="mt-4 text-lg font-semibold">Can't be checked from video</h2>
              <ul className="mt-2 space-y-2">
                {result.refusals.map((r) => (
                  <li key={r.line} className="rounded border-2 border-red-800/30 bg-red-50 p-3">
                    <span className="font-medium">{r.line}</span>
                    <span className="block text-sm opacity-80">{r.reason}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          <button
            type="button"
            onClick={useChecklist}
            className="mt-4 min-h-12 w-full rounded bg-emerald-900 px-4 py-3 font-semibold text-white"
          >
            Use this checklist
          </button>
        </section>
      )}
    </main>
  );
}
