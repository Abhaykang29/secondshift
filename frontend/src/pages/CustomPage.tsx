import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { CustomChecklistResponse } from "../api/extra";
import Banner from "../components/ui/Banner";
import Button from "../components/ui/Button";

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
    <main className="mx-auto w-full max-w-[720px] p-4 pb-28">
      <h1 className="text-[24px] font-[650] leading-[30px] tracking-[-0.01em]">Your own checklist</h1>
      <p className="mt-2 text-text-2">
        Type what you want checked, one line each (3 to 10 lines). Each line is
        turned into something a camera can verify - or refused, with the reason.
      </p>
      <div className="mt-2">
        <Banner kind="warn">Custom checklist - not reviewed by an expert</Banner>
      </div>
      <textarea
        className="mt-4 min-h-44 w-full rounded-btn border border-border-strong bg-surface p-3 text-[15px]"
        placeholder={
          "loose cords across the walkway\nboxes stacked above shoulder height\nfire extinguisher mounted by the exit"
        }
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <p className="mt-1 font-mono text-[12.5px] tabular-nums text-text-3">{lines.length} line(s) - needs 3 to 10</p>
      <Button
        type="button"
        variant="primary"
        size="lg"
        fullWidth
        disabled={busy || lines.length < 3 || lines.length > 10}
        onClick={compile}
        className="mt-3"
      >
        {busy ? "Compiling..." : "Compile my checklist"}
      </Button>
      {error && (
        <p role="alert" className="mt-3 rounded-card bg-bad-bg p-3 text-[14px] text-bad">
          {error}
        </p>
      )}
      {result && (
        <section className="mt-5">
          <h2 className="text-[17px] font-semibold">What will be checked</h2>
          <ul className="mt-2 space-y-2">
            {result.items.map((item) => (
              <li key={item.id} className="rounded-card border border-border bg-surface p-3">
                <span className="font-medium">{item.title}</span>
                <span className="block text-[14px] text-text-2">
                  looks for: {item.sam_prompts.join(", ")}
                  {item.thin_object ? " · close-up crops for thin objects" : ""}
                </span>
              </li>
            ))}
          </ul>
          {result.refusals.length > 0 && (
            <>
              <h2 className="mt-4 text-[17px] font-semibold">Can't be checked from video</h2>
              <ul className="mt-2 space-y-2">
                {result.refusals.map((r) => (
                  <li key={r.line} className="rounded-card border border-dashed border-border-strong bg-surface p-3">
                    <span className="font-medium">{r.line}</span>
                    <span className="block text-[14px] text-text-2">{r.reason}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          <Button
            type="button"
            variant="primary"
            size="lg"
            fullWidth
            onClick={useChecklist}
            className="mt-4"
          >
            Use this checklist
          </Button>
        </section>
      )}
    </main>
  );
}
