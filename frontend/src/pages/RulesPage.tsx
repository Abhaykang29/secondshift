import { useState } from "react";
import { HelpCircle } from "lucide-react";
import { api } from "../api/client";
import en from "../i18n/en.json";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Chip from "../components/ui/Chip";

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
    <main className="mx-auto max-w-2xl p-4">
      <h1 className="text-[24px] font-[650] leading-[30px] tracking-[-0.01em]">Rules</h1>
      <p className="mt-2 text-[15px] leading-[22px] text-text-2">
        Type what you want checked, in plain words. If a camera can't see it, I'll say so -
        and offer what I can check instead.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <Button key={ex} type="button" variant="secondary"
            onClick={() => { setText(ex); void compile(ex, mode); }}>
            {ex}
          </Button>
        ))}
      </div>
      <label className="mt-4 block">
        Your rule
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3}
          className="mt-1 block w-full rounded-btn border border-border-strong bg-surface p-3 text-[15px]" />
      </label>
      <label className="mt-2 block">
        Mode{" "}
        <select value={mode} onChange={(e) => setMode(e.target.value)}
          className="rounded-btn border border-border-strong bg-surface px-3 py-2 text-[15px]">
          <option value="checkup">Check-up (at each re-check)</option>
          <option value="watch">Watch (one spot, live)</option>
        </select>
      </label>
      <Button type="button" variant="primary" fullWidth disabled={!text.trim()}
        className="mt-4" onClick={() => void compile(text, mode)}>
        Compile this rule
      </Button>

      {result?.status === "compiled" && (
        <section aria-label="Compiled rule" className="mt-8">
        <Card>
          <Chip variant="accent">Compiled</Chip>
          <p className="mt-3 text-[15px] font-semibold leading-[22px]">{result.human_summary}</p>
          {(result.conditions ?? []).length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {(result.conditions ?? []).map((c) => (
                <Chip key={c.primitive}>
                  <span className="font-mono text-[12.5px]">{c.primitive}</span>
                </Chip>
              ))}
            </div>
          )}
          <Button type="button" variant="ghost" className="mt-2"
            onClick={() => setShowJson((v) => !v)}>
            {showJson ? "Hide" : "Show"} JSON
          </Button>
          {showJson && (
            <pre className="mt-2 overflow-auto rounded-btn bg-surface-2 p-3 font-mono text-[12px] leading-[18px]">
              {JSON.stringify(result, null, 2)}
            </pre>
          )}
        </Card>
        </section>
      )}
      {result?.status === "refused" && (
        <section aria-label="Refused rule" className="mt-8">
        <Card dashed>
          <span className="inline-flex h-6 items-center gap-1.5 rounded-chip border border-dashed border-border-strong bg-unk-bg px-2.5 text-[12px] font-semibold text-unk">
            <HelpCircle size={14} strokeWidth={1.75} aria-hidden />
            Can&rsquo;t be checked by camera
          </span>
          <h2 className="mt-3 text-[16px] font-semibold leading-[22px]">{en.refusal_lead_in}</h2>
          <p className="mt-1 text-[14px] leading-[20px] text-text-2">{result.refusal_reason}</p>
          <div className="mt-3 grid gap-2">
            {(result.alternatives ?? []).map((alt) => (
              <Button key={alt} type="button" variant="secondary" fullWidth
                onClick={() => { setText(alt); void compile(alt, mode); }}>
                {alt}
              </Button>
            ))}
          </div>
        </Card>
        </section>
      )}
      {result?.status === "needs_clarification" && (
        <section aria-label="Needs clarification" className="mt-8">
        <Card>
          <h2 className="text-[16px] font-semibold leading-[22px]">One question first</h2>
          <p className="mt-1 text-[15px] leading-[22px]">{result.clarifying_question}</p>
        </Card>
        </section>
      )}
    </main>
  );
}
