import { useState } from "react";

interface Answer { answer: string; follow_up?: string | null }

/**
 * Ask about a report (spec 5.1 step 6): answers come only from the
 * check-up's own report data; out-of-scope questions get the honest
 * refusal. Needs the checkup id from the report URL.
 */
export default function AskPage() {
  const [checkupId, setCheckupId] = useState("");
  const [question, setQuestion] = useState("How do I fix the rug?");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [error, setError] = useState("");

  async function ask() {
    setError("");
    const res = await fetch("/api/ask", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ checkup_id: checkupId, question }),
    });
    if (!res.ok) { setError("No report for that checkup id yet."); return; }
    setAnswer((await res.json()) as Answer);
  }

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">Ask about a report</h1>
      <label className="mt-4 block">Checkup ID (from the report page URL)
        <input value={checkupId} onChange={(e) => setCheckupId(e.target.value)}
          className="mt-1 block w-full rounded border p-3" />
      </label>
      <label className="mt-3 block">Your question
        <input value={question} onChange={(e) => setQuestion(e.target.value)}
          className="mt-1 block w-full rounded border p-3" />
      </label>
      {error && <p role="alert" className="mt-2 text-red-700">{error}</p>}
      <button type="button" disabled={!checkupId.trim()} onClick={() => void ask()}
        className="mt-4 w-full rounded bg-blue-700 px-4 py-3 text-white disabled:opacity-40">
        Ask
      </button>
      {answer && (
        <section className="mt-5 rounded border p-4" aria-label="Answer">
          <p>{answer.answer}</p>
          {answer.follow_up && <p className="mt-2 text-sm opacity-80">{answer.follow_up}</p>}
        </section>
      )}
    </main>
  );
}
