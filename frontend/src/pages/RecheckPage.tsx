import { useState } from "react";
import { useParams } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { api } from "../api/client";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Chip from "../components/ui/Chip";
import TallyBar from "../components/ui/TallyBar";
import VerdictChip, { type VerdictKind } from "../components/ui/VerdictChip";

interface RecheckItemView {
  item_id: string; room: string; status: string; reason: string;
}
interface RecheckView {
  items: RecheckItemView[];
  score_before: number; score_after: number;
  rule_outcomes: { rule_id: string; outcome: string; reason: string }[];
}

const CHIP: Record<string, VerdictKind> = {
  resolved: "fixed", still_present: "still", new: "new", cannot_tell: "cannot",
};

/**
 * Re-check page (spec 5.1 step 8): run the fixed-home re-check and show
 * the diff - Resolved / Still there / New / Couldn't tell - plus the
 * home score before and after, and saved rule outcomes.
 */
export default function RecheckPage() {
  const { id = "" } = useParams();
  const [recheck, setRecheck] = useState<RecheckView | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      const result = (await api.recheck(id, "parent_home_fixed")) as unknown as RecheckView;
      setRecheck(result);
    } catch {
      setError("Run a scan first - a re-check needs a report to compare with.");
    }
    setBusy(false);
  }

  return (
    <main className="mx-auto max-w-2xl p-4">
      <h1 className="text-[24px] font-[650] leading-[30px] tracking-[-0.01em]">Re-check</h1>
      <p className="mt-2 text-[15px] leading-[22px] text-text-2">
        Film the home again the same way. I'll show what was fixed, what's still there,
        and anything new. (Demo: the "fixed home" re-check.)
      </p>
      {error && <p role="alert" className="mt-3 text-bad">{error}</p>}
      <Button type="button" variant="primary" fullWidth icon={RefreshCw} disabled={busy}
        className="mt-4" onClick={() => void run()}>
        {busy ? "Re-checking..." : "Run the re-check"}
      </Button>
      {recheck && (
        <section className="mt-8" aria-label="Re-check results">
          <p className="text-[17px] font-semibold leading-[24px]">
            Home score:{" "}
            <span className="font-mono tabular-nums">{recheck.score_before}</span> to{" "}
            <span className="font-mono tabular-nums">{recheck.score_after}</span>
          </p>
          <div className="mt-3">
            <TallyBar
              compact
              counts={{
                bad: recheck.items.filter(
                  (i) => i.status === "still_present" || i.status === "new",
                ).length,
                warn: 0,
                unk: recheck.items.filter((i) => i.status === "cannot_tell").length,
                ok: recheck.items.filter((i) => i.status === "resolved").length,
              }}
              labels={[["problem", "problems"], ["needs a look", "needs a look"], ["can't tell", "can't tell"], ["fixed", "fixed"]]}
            />
          </div>
          <div className="mt-3 flex flex-col gap-3">
            {recheck.items.map((item) => (
              <Card key={item.item_id}>
                <div className="flex flex-wrap items-center gap-2">
                  {CHIP[item.status] ? (
                    <VerdictChip kind={CHIP[item.status]} />
                  ) : (
                    <Chip>{item.status}</Chip>
                  )}
                  <span className="font-mono text-[12.5px] tabular-nums text-text-2">
                    {item.item_id}
                  </span>
                  <span className="text-[13px] text-text-3">({item.room})</span>
                </div>
                <p className="mt-2 text-[14px] leading-[20px] text-text-2">{item.reason}</p>
              </Card>
            ))}
          </div>
          {recheck.rule_outcomes.length > 0 && (
            <>
              <h2 className="mt-8 text-[17px] font-semibold leading-[24px]">Saved rules</h2>
              <ul className="mt-2">
                {recheck.rule_outcomes.map((o) => (
                  <li key={o.rule_id} className="mt-1.5 flex items-baseline gap-2 text-[14px]">
                    <span className="font-mono text-[12.5px] font-semibold tabular-nums">
                      {o.outcome.toUpperCase()}
                    </span>
                    <span className="text-text-2">- {o.reason}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}
    </main>
  );
}
