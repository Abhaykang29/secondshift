import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { RefilmInstruction, Report } from "../api/types";

/**
 * Guided re-film card (final pass, item 1c): the report's cannot-tell
 * items as filming instructions, grouped by room, at most 5 shown
 * (the stored order is risk-ranked). "Film these now" records a
 * <=60s clip in the browser (MediaRecorder) and uploads it to the
 * refilm endpoint; the merged report comes back and replaces the
 * page's report, with resolved items labelled "from follow-up clip".
 * "Read aloud" uses the browser's speechSynthesis - no API cost.
 * Where camera capture is unavailable, a file input with
 * capture="environment" is the fallback (mobile browsers open the
 * camera from it).
 */
export default function RefilmCard({
  checkupId,
  instructions,
  onMerged,
}: {
  checkupId: string;
  instructions: RefilmInstruction[];
  onMerged: (report: Report) => void;
}) {
  const [showRecorder, setShowRecorder] = useState(false);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [clip, setClip] = useState<Blob | null>(null);
  const [clipUrl, setClipUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<number | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const shown = instructions.slice(0, 5);
  const byRoom = new Map<string, RefilmInstruction[]>();
  for (const ins of shown) {
    const list = byRoom.get(ins.room) ?? [];
    list.push(ins);
    byRoom.set(ins.room, list);
  }
  const canRecord =
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== "undefined";
  const canSpeak = typeof window !== "undefined" && "speechSynthesis" in window;

  function stopCamera() {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (timerRef.current) window.clearInterval(timerRef.current);
    timerRef.current = null;
  }

  useEffect(() => stopCamera, []);

  async function startRecording() {
    setMessage(null);
    setClip(null);
    setClipUrl(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "video/mp4" });
        setClip(blob);
        setClipUrl(URL.createObjectURL(blob));
        stopCamera();
      };
      recorder.start(250);
      setRecording(true);
      setSeconds(0);
      timerRef.current = window.setInterval(() => {
        setSeconds((s) => {
          if (s + 1 >= 60) stopRecording();
          return s + 1;
        });
      }, 1000);
    } catch {
      setMessage("The camera could not be opened here. Use the file picker below instead.");
    }
  }

  function stopRecording() {
    setRecording(false);
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    else stopCamera();
  }

  async function upload(blob: Blob, name: string) {
    setUploading(true);
    setMessage("Checking your clip - this can take a couple of minutes...");
    try {
      const file = new File([blob], name, { type: blob.type || "video/mp4" });
      const merged = await api.refilm(checkupId, file);
      onMerged(merged);
      setShowRecorder(false);
      setClip(null);
      setMessage(null);
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "The clip could not be checked. Please try again.",
      );
    } finally {
      setUploading(false);
    }
  }

  function readAloud() {
    if (!canSpeak) return;
    window.speechSynthesis.cancel();
    for (const ins of shown) {
      window.speechSynthesis.speak(new SpeechSynthesisUtterance(ins.instruction));
    }
  }

  if (instructions.length === 0) return null;
  return (
    <section aria-label="I couldn't see these" className="mt-8 rounded border-2 border-[#1f3d2b] bg-white p-4">
      <h2 className="text-xl font-semibold">I couldn&rsquo;t see these</h2>
      <p className="mt-1 text-sm opacity-80">
        A short follow-up clip can settle {instructions.length === 1 ? "this one" : `these ${instructions.length}`}.
        Film one clip of up to 60 seconds, following the steps in order.
      </p>
      {[...byRoom.entries()].map(([room, items]) => (
        <div key={room} className="mt-3">
          <h3 className="font-medium capitalize">{room}</h3>
          <ol className="mt-1 list-decimal pl-6">
            {items.map((ins) => (
              <li key={ins.item_id} className="mt-1">
                {ins.instruction}{" "}
                <span className="rounded-full bg-[#e9f2ec] px-2 py-0.5 text-xs font-medium text-[#1f3d2b]">
                  Show: {ins.what_to_show}
                </span>
              </li>
            ))}
          </ol>
        </div>
      ))}
      {instructions.length > shown.length && (
        <p className="mt-2 text-sm opacity-75">
          +{instructions.length - shown.length} more - film the rooms above first, then this
          list updates.
        </p>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setShowRecorder((v) => !v)}
          className="rounded bg-[#1f3d2b] px-4 py-3 font-medium text-white"
        >
          🎥 Film these now
        </button>
        {canSpeak && (
          <button type="button" onClick={readAloud} className="rounded border px-4 py-3">
            🔊 Read aloud
          </button>
        )}
      </div>
      {showRecorder && (
        <div className="mt-4">
          {canRecord ? (
            <>
              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
                className="aspect-video w-full rounded bg-neutral-800"
              />
              {clipUrl && !recording && (
                <video src={clipUrl} controls className="mt-2 aspect-video w-full rounded" />
              )}
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {!recording && !clip && (
                  <button type="button" onClick={() => void startRecording()} className="rounded bg-red-700 px-4 py-2 text-white">
                    ● Start (max 60s)
                  </button>
                )}
                {recording && (
                  <button type="button" onClick={stopRecording} className="rounded bg-red-700 px-4 py-2 text-white">
                    ■ Stop - {seconds}s / 60s
                  </button>
                )}
                {clip && !uploading && (
                  <>
                    <button
                      type="button"
                      onClick={() => void upload(clip, "refilm.mp4")}
                      className="rounded bg-[#1f3d2b] px-4 py-2 text-white"
                    >
                      Use this clip
                    </button>
                    <button type="button" onClick={() => void startRecording()} className="rounded border px-4 py-2">
                      Retake
                    </button>
                  </>
                )}
              </div>
            </>
          ) : (
            <label className="block">
              Pick or record a clip (up to 60 seconds)
              <input
                type="file"
                accept="video/*"
                capture="environment"
                className="mt-1 block w-full rounded border p-3"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void upload(f, f.name);
                }}
              />
            </label>
          )}
          {canRecord && (
            <label className="mt-3 block text-sm">
              Or upload a clip you already filmed
              <input
                type="file"
                accept="video/*"
                className="mt-1 block w-full rounded border p-3"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void upload(f, f.name);
                }}
              />
            </label>
          )}
          {uploading && <p className="mt-2 text-sm">Uploading and checking...</p>}
          {message && <p className="mt-2 text-sm" role="status">{message}</p>}
        </div>
      )}
    </section>
  );
}
