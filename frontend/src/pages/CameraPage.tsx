import { useEffect, useRef, useState } from "react";

/**
 * The phone-as-camera page (Phase 6.5): open this on the old phone,
 * allow the camera, and it streams JPEG frames over a WebSocket to the
 * backend's /api/camera ingest. iPhone Safari requires HTTPS for the
 * camera - serve the app with `make dev-https` (self-signed local cert).
 * Nothing is recorded on the phone or the server; frames are processed
 * and discarded (see PRIVACY.md).
 */
export default function CameraPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [status, setStatus] = useState("Tap Start to share this phone's camera with SecondShift.");
  const streamRef = useRef<MediaStream | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<number | null>(null);

  async function start() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" }, audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      const socket = new WebSocket(`${proto}://${window.location.hostname}:8000/api/camera`);
      socket.binaryType = "arraybuffer";
      socketRef.current = socket;
      socket.onopen = () => {
        setStatus("Streaming frames to SecondShift (nothing is recorded).");
        const canvas = document.createElement("canvas");
        canvas.width = 640; canvas.height = 360;
        const ctx = canvas.getContext("2d");
        timerRef.current = window.setInterval(() => {
          if (!videoRef.current || !ctx || socket.readyState !== WebSocket.OPEN) return;
          ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
          canvas.toBlob((blob) => {
            if (blob) void blob.arrayBuffer().then((buf) => socket.send(buf));
          }, "image/jpeg", 0.7);
        }, 500);
      };
      socket.onclose = () => setStatus("Connection closed.");
    } catch {
      setStatus("Camera permission was refused, or this page is not on HTTPS (iPhone Safari needs HTTPS).");
    }
  }

  function stop() {
    if (timerRef.current) window.clearInterval(timerRef.current);
    socketRef.current?.close();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    setStatus("Stopped.");
  }

  useEffect(() => () => stop(), []);

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">Phone camera for Watch</h1>
      <p className="mt-2" role="status">{status}</p>
      <video ref={videoRef} autoPlay playsInline muted className="mt-4 w-full rounded bg-black" />
      <div className="mt-4 flex gap-3">
        <button type="button" onClick={() => void start()} className="rounded bg-blue-700 px-4 py-3 text-white">
          Start streaming
        </button>
        <button type="button" onClick={stop} className="rounded border px-4 py-3">Stop</button>
      </div>
      <p className="mt-3 text-sm opacity-80">
        Prop the phone facing the one spot the rule watches. Frames only - no recording, no audio.
      </p>
    </main>
  );
}
