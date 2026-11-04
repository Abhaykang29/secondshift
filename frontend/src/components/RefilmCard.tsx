import { useEffect, useRef, useState } from "react";
import { Camera, Video, Volume2 } from "lucide-react";
import { api } from "../api/client";
import type { RefilmInstruction, Report } from "../api/types";
import Button from "./ui/Button";
import Chip from "./ui/Chip";

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
    <section aria-label="I couldn't see these" className="rounded-card bg-surface shadow-card p-4">
      <div className="flex items-center gap-2">
        <h2 className="text-[17px] font-semibold leading-[24px]">I couldn&rsquo;t see these</h2>
        <Chip>
          <span className="font-mono tabular-nums">{instructions.length}</span>
        </Chip>
      </div>
      <p className="mt-1 text-[14px] leading-[20px] text-text-2">
        A short follow-up clip can settle {instructions.length === 1 ? "this one" : `these ${instructions.length}`}.
        Film one clip of up to 60 seconds, following the steps in order.
      </p>
      {[...byRoom.entries()].map(([room, items]) => (
        <div key={room} className="mt-4">
          <h3 className="text-[13px] font-semibold capitalize text-text-2">{room}</h3>
          <ul className="mt-1.5 space-y-2">
            {items.map((ins) => (
              <li key={ins.item_id} className="flex items-start gap-2">
                <Camera size={18} strokeWidth={1.75} className="mt-0.5 shrink-0 text-accent" aria-hidden />
                <span className="flex-1 text-[15px] leading-[22px]">{ins.instruction}</span>
                <Chip className="shrink-0">Show: {ins.what_to_show}</Chip>
              </li>
            ))}
          </ul>
        </div>
      ))}
      {instructions.length > shown.length && (
        <p className="mt-2 text-[13px] text-text-3">
          +{instructions.length - shown.length} more - film the rooms above first, then this
          list updates.
        </p>
      )}
      <div className="mt-4 space-y-2">
        <Button variant="primary" size="lg" fullWidth icon={Video} onClick={() => setShowRecorder((v) => !v)}>
          Film these now
        </Button>
        {canSpeak && (
          <Button variant="secondary" icon={Volume2} onClick={readAloud}>
            Read aloud
          </Button>
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
                className="aspect-video w-full rounded-card bg-surface-3"
              />
              {clipUrl && !recording && (
                <video src={clipUrl} controls className="mt-2 aspect-video w-full rounded-card" />
              )}
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {!recording && !clip && (
                  <Button variant="primary" onClick={() => void startRecording()}>
                    Start (max 60s)
                  </Button>
                )}
                {recording && (
                  <Button variant="secondary" onClick={stopRecording}>
                    Stop - {seconds}s / 60s
                  </Button>
                )}
                {clip && !uploading && (
                  <>
                    <Button variant="primary" onClick={() => void upload(clip, "refilm.mp4")}>
                      Use this clip
                    </Button>
                    <Button variant="secondary" onClick={() => void startRecording()}>
                      Retake
                    </Button>
                  </>
                )}
              </div>
            </>
          ) : (
            <label className="block text-[14px] text-text-2">
              Pick or record a clip (up to 60 seconds)
              <input
                type="file"
                accept="video/*"
                capture="environment"
                className="mt-1 block w-full rounded-btn border border-border-strong bg-surface p-3 text-[15px] text-text"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void upload(f, f.name);
                }}
              />
            </label>
          )}
          {canRecord && (
            <label className="mt-3 block text-[14px] text-text-2">
              Or upload a clip you already filmed
              <input
                type="file"
                accept="video/*"
                className="mt-1 block w-full rounded-btn border border-border-strong bg-surface p-3 text-[15px] text-text"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void upload(f, f.name);
                }}
              />
            </label>
          )}
          {uploading && <p className="mt-2 text-[14px] text-text-2">Uploading and checking...</p>}
          {message && <p className="mt-2 text-[14px] text-text-2" role="status">{message}</p>}
        </div>
      )}
    </section>
  );
}
