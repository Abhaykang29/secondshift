import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

const STEPS = [
  "Extracting frames", "Finding hazards", "Confirming with SAM",
  "Studying the routine", "Planning fixes", "Drawing after pictures",
];

/**
 * Processing screen (spec 5.1 step 5). The scan runs as a persisted job;
 * this page shows the step list. With ?job=<id> it polls job status.
 */
export default function Processing() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const [status, setStatus] = useState("The scan runs step by step; finished steps are never repeated.");
  const jobId = params.get("job");

  useEffect(() => {
    if (!jobId) return;
    let stop = false;
    const tick = async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        const job = (await res.json()) as { status: string; completed_steps: string[] };
        if (!stop) setStatus(`Job ${job.status}: ${job.completed_steps.join(", ")}`);
      } catch {
        if (!stop) setStatus("Could not read job status.");
      }
    };
    void tick();
    const timer = setInterval(() => void tick(), 1500);
    return () => { stop = true; clearInterval(timer); };
  }, [jobId]);

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">Checking checkup {id}</h1>
      <ol className="mt-4 list-decimal pl-6">
        {STEPS.map((s) => <li key={s} className="py-1">{s}</li>)}
      </ol>
      <p className="mt-4" role="status">{status}</p>
    </main>
  );
}
