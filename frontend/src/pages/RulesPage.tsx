import { useState } from "react";
import { api } from "../api/client";
import en from "../i18n/en.json";

const EXAMPLES = [
  "Make sure there's no rug on the stairs.",
  "Check that the hallway night light is still there.",
  "Tell me if the baby gate at the top of the stairs is left open for more than 30 seconds.",
  "Warn me before Mom falls.",
  "Tell me if the gate is open.",
  "Tell me if the baby is crying.",
];

interface RuleResult {
  status: string;
  human_summary: string;
  refusal_reason?: string | null;
  clarifying_question?: string | null;
  alternatives?: string[];
  conditions?: { primitive: string }[];
}

/**
 * Rule compiler page (spec 5.1 step 9 / 5.2 step 4): type a sentence,
 * get a compiled card, a refusal card with tappable alternatives, or one
 * clarifying question. Every rule answers MET / NOT MET / CANNOT TELL.
 */
export default function RulesPage() {
  const [text, setText] = useState("");
  const [mode, setMode] = useState("checkup");
  const [result, setResult] = useState<RuleResult | null>(null);
  const [showJson, setShowJson] = useState(false);

  async function compile(value: string, modeHint: string) {
    const spec = (await api.compileRule(value, modeHint)) as unknown as RuleResult;
    setResult(spec);
  }

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">Rules</h1>
      <p className="mt-2">
        Type what you want checked, in plain words. If a camera can't see it, I'll say so -
        and offer what I can check instead.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button key={ex} type="button" className="rounded border px-3 py-2 text-sm"
            onClick={() => { setText(ex); void compile(ex, mode); }}>
            {ex}
          </button>
        ))}
      </div>
      <label className="mt-4 block">
        Your rule
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3}
          className="mt-1 block w-full rounded border p-3" />
      </label>
      <label className="mt-2 block">
        Mode{" "}
        <select value={mode} onChange={(e) => setMode(e.target.value)} className="rounded border p-2">
          <option value="checkup">Check-up (at each re-check)</option>
          <option value="watch">Watch (one spot, live)</option>
        </select>
      </label>
      <button type="button" disabled={!text.trim()} onClick={() => void compile(text, mode)}
        className="mt-4 w-full rounded bg-blue-700 px-4 py-3 text-white disabled:opacity-40">
        Compile this rule
      </button>

      {result?.status === "compiled" && (
        <section className="mt-6 rounded border border-green-600 p-4" aria-label="Compiled rule">
          <h2 className="font-semibold">Compiled</h2>
          <p className="mt-1">{result.human_summary}</p>
          <p className="mt-1 text-sm opacity-80">
            Checks: {(result.conditions ?? []).map((c) => c.primitive).join(" + ")}
          </p>
          <button type="button" className="mt-2 text-sm underline"
            onClick={() => setShowJson((v) => !v)}>
            {showJson ? "Hide" : "Show"} JSON
          </button>
          {showJson && <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(result, null, 2)}</pre>}
        </section>
      )}
      {result?.status === "refused" && (
        <section className="mt-6 rounded border border-red-500 p-4" aria-label="Refused rule">
          <h2 className="font-semibold">{en.refusal_lead_in}</h2>
          <p className="mt-1">{result.refusal_reason}</p>
          <div className="mt-3 grid gap-2">
            {(result.alternatives ?? []).map((alt) => (
              <button key={alt} type="button" className="rounded border px-3 py-2 text-left"
                onClick={() => { setText(alt); void compile(alt, mode); }}>
                {alt}
              </button>
            ))}
          </div>
        </section>
      )}
      {result?.status === "needs_clarification" && (
        <section className="mt-6 rounded border border-amber-500 p-4" aria-label="Needs clarification">
          <h2 className="font-semibold">One question first</h2>
          <p className="mt-1">{result.clarifying_question}</p>
        </section>
      )}
    </main>
  );
}
