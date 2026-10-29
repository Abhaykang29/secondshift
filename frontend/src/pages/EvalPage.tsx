import { useEffect, useState } from "react";
import { api } from "../api/client";

interface RunView {
  config: string;
  totals: { precision: number; recall: number; f1: number };
  estimated_cost_usd: number;
  wall_time_s: number;
}
interface EvalView {
  runs: RunView[];
  compiler: { sentences: number; status_accuracy: number; primitive_accuracy_on_compiled: number };
  dataset: string;
  run_dir?: string;
}

/**
 * /eval page (spec 5.3): the latest harness run - ablation table and
 * compiler metrics, with the honest mock-data caveat front and centre.
 */
export default function EvalPage() {
  const [data, setData] = useState<EvalView | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.evalLatest()
      .then((d) => setData(d as unknown as EvalView))
      .catch(() => setError("No eval run yet - run `make eval` first."));
  }, []);

  if (error) return <main className="mx-auto max-w-2xl p-6"><p role="alert">{error}</p></main>;
  if (!data) return <main className="mx-auto max-w-2xl p-6"><p>Loading eval...</p></main>;

  return (
    <main className="relative mx-auto max-w-2xl overflow-hidden p-6">
      <div aria-hidden className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
        <span className="-rotate-45 text-6xl font-bold tracking-widest text-red-600/15">MOCK DATA</span>
      </div>
      <p className="inline-block rounded bg-red-700 px-3 py-1 font-semibold text-white">MOCK DATA</p>
      <h1 className="mt-2 text-2xl font-semibold">Evaluation</h1>
      <p className="mt-2 text-sm opacity-80">
        Run {data.run_dir} - {data.dataset}. These numbers validate the harness on mock
        scenarios; real accuracy needs human-labelled captures (TODO(TEAM)).
      </p>
      <table className="mt-4 w-full border-collapse">
        <thead>
          <tr>{["Config", "Precision", "Recall", "F1", "Est. cost", "Wall time"].map((h) => (
            <th key={h} className="border p-2 text-left">{h}</th>
          ))}</tr>
        </thead>
        <tbody>
          {data.runs.map((run) => (
            <tr key={run.config}>
              <td className="border p-2">{run.config}</td>
              <td className="border p-2">{run.totals.precision}</td>
              <td className="border p-2">{run.totals.recall}</td>
              <td className="border p-2">{run.totals.f1}</td>
              <td className="border p-2">${run.estimated_cost_usd}</td>
              <td className="border p-2">{run.wall_time_s}s</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-4">
        Rule compiler on {data.compiler.sentences} Appendix B sentences: status accuracy{" "}
        {data.compiler.status_accuracy}, primitive accuracy{" "}
        {data.compiler.primitive_accuracy_on_compiled}.
      </p>
      <p className="mt-2">
        Reading the table: spark_only keeps the planted false positive (a pet bowl that
        isn't there); adding SAM verification removes it - precision 0.94 to 1.0.
      </p>
    </main>
  );
}
