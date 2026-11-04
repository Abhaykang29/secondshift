import { useEffect, useRef, useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import Card from "../components/ui/Card";

/**
 * Processing screen (Pass 3 spec 4.3 step 4, redesign spec 5.7): a
 * vertical stepper with real counts while the check runs. The scan
 * endpoint runs the job synchronously and stores it
 * (GET /api/jobs/{id}); with ?job=<id> this page just polls that job.
 * Otherwise it starts the scan itself (with ?capture=<id> for an
 * uploaded walkthrough) and shows: frames from the capture's keyframe
 * list, then the pipeline steps as the request progresses. Leaving is
 * fine - the job is persisted server-side.
 */

type StepState = "done" | "active" | "todo";

interface StepView {
  label: string;
  detail?: string;
  state: StepState;
}

const PIPELINE_STEPS = [
  "People blurred",
  "Proposing hazards",
  "SAM checks",
  "Room sweep",
  "Fix plans",
  "After photos",
];

export default function Processing() {
  const { id = "" } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const jobId = params.get("job");
  const captureId = params.get("capture");
  const [frames, setFrames] = useState<{ total: number; usable: number } | null>(null);
  const [phase, setPhase] = useState<"running" | "done" | "failed">("running");
  const [jobDone, setJobDone] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const startedRef = useRef(false);

  // Elapsed timer.
  useEffect(() => {
    if (phase !== "running") return;
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [phase]);

  // Real frame counts for an uploaded capture.
  useEffect(() => {
    if (!captureId) return;
    api
      .keyframes(captureId)
      .then((r) =>
        setFrames({
          total: r.keyframes.length,
          usable: r.keyframes.filter((k) => k.usable).length,
        }),
      )
      .catch(() => setFrames(null));
  }, [captureId]);

  // Poll an existing job (deep link with ?job=).
  useEffect(() => {
    if (!jobId) return;
    let stop = false;
    const tick = async () => {
      try {
        const job = await api.job(jobId);
        if (stop) return;
        setJobDone(job.completed_steps);
        if (job.status === "done") {
          setPhase("done");
          navigate(`/checkup/${id}/report`);
        } else if (job.status === "failed") {
          setPhase("failed");
          setError(job.error ?? "The check failed.");
        }
      } catch {
        if (!stop) setError("Could not read job status.");
      }
    };
    void tick();
    const timer = setInterval(() => void tick(), 1500);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  }, [jobId, id, navigate]);

  // Start the scan when we arrived from the capture step.
  useEffect(() => {
    if (jobId || startedRef.current) return;
    startedRef.current = true;
    api
      .scan(id, undefined, captureId ?? undefined)
      .then(() => {
        setPhase("done");
        navigate(`/checkup/${id}/report`);
      })
      .catch((e: unknown) => {
        setPhase("failed");
        setError(e instanceof Error ? e.message : "The check failed to start.");
      });
  }, [jobId, id, captureId, navigate]);

  const scanStepDone = jobDone.includes("scan") || phase === "done";
  const steps: StepView[] = [
    {
      label: "Frames extracted",
      detail: frames
        ? `${frames.total} frames, ${frames.usable} clear enough to check`
        : captureId
          ? "Reading the video..."
          : "Demo home (recorded frames)",
      state: frames || !captureId || phase !== "running" ? "done" : "active",
    },
    ...PIPELINE_STEPS.map((label, i): StepView => {
      let state: StepState = "todo";
      if (phase === "done") state = "done";
      else if (label === "Fix plans" && jobDone.includes("fixes")) state = "done";
      else if (label === "After photos" && jobDone.includes("visualize")) state = "done";
      else if (i <= 3 && scanStepDone) state = "done";
      else if (i <= 3 && phase === "running") state = "active";
      else if (i === 4 && scanStepDone) state = "active";
      return { label, state };
    }),
  ];

  const mm = Math.floor(elapsed / 60);
  const ss = String(elapsed % 60).padStart(2, "0");

  return (
    <main className="pt-1">
      <h1 className="text-[24px] font-[650] leading-[30px] tracking-[-0.01em]">
        Checking the home
      </h1>
      <p className="mt-2" role="status">
        {phase === "running" && `Working... ${mm}:${ss} so far. A 1-minute video usually takes 3-7 minutes.`}
        {phase === "done" && "Done - taking you to the report."}
        {phase === "failed" && "Something went wrong."}
      </p>
      <div className="mt-5">
        <Card>
          <ol className="grid gap-4">
            {steps.map((step) => (
              <li key={step.label} className="flex items-center gap-3">
                {step.state === "done" ? (
                  <span
                    className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ok"
                    aria-hidden
                  >
                    <Check size={14} strokeWidth={1.75} className="text-text-inverse" />
                  </span>
                ) : step.state === "active" ? (
                  <span
                    className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-accent"
                    aria-hidden
                  >
                    <Loader2 size={14} strokeWidth={1.75} className="animate-spin text-accent" />
                  </span>
                ) : (
                  <span
                    className="h-6 w-6 shrink-0 rounded-full border border-border-strong"
                    aria-hidden
                  />
                )}
                <span className="min-w-0 flex-1">
                  <span className="text-[15px] font-medium">{step.label}</span>
                  {step.detail && (
                    <span className="block text-[14px] text-text-2">{step.detail}</span>
                  )}
                </span>
                {step.state === "active" && (
                  <span className="shrink-0 font-mono text-[12.5px] tabular-nums text-text-3">
                    Checking now...
                  </span>
                )}
              </li>
            ))}
          </ol>
        </Card>
      </div>
      {error && (
        <p role="alert" className="mt-4 text-bad">
          {error}
        </p>
      )}
      <div className="mt-5">
        <Card>
          <p className="text-[14px] text-text-2">
            You can leave this screen — the check keeps running, and the home
            card will show the report when it is ready.
          </p>
        </Card>
      </div>
    </main>
  );
}
