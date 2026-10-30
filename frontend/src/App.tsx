import { useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Footer from "./components/Footer";
import TabBar from "./components/TabBar";
import AskPage from "./pages/AskPage";
import CameraPage from "./pages/CameraPage";
import CheckupNew from "./pages/CheckupNew";
import CustomPage from "./pages/CustomPage";
import EvalLabelPage from "./pages/EvalLabelPage";
import EvalPage from "./pages/EvalPage";
import Fixes from "./pages/Fixes";
import Home from "./pages/Home";
import HomesPage from "./pages/HomesPage";
import LearnPage from "./pages/LearnPage";
import LivePage from "./pages/LivePage";
import Processing from "./pages/Processing";
import RecheckPage from "./pages/RecheckPage";
import ReportPage from "./pages/ReportPage";
import RulesPage from "./pages/RulesPage";
import SettingsPage from "./pages/SettingsPage";
import WatchLive from "./pages/WatchLive";
import WatchSetup from "./pages/WatchSetup";

/**
 * App shell (Pass 3 spec 4.1-4.2): installable PWA, phone-first column,
 * bottom tab bar (Check / Live / Homes / Learn). Every pre-PWA route
 * stays reachable - the tab pages link into the same flows.
 */

function MockBanner() {
  const [mode, setMode] = useState<string>("");
  useEffect(() => {
    fetch("/api/settings")
      .then((r) => r.json())
      .then((d: { provider_mode?: string }) => setMode(d.provider_mode ?? ""))
      .catch(() => setMode(""));
  }, []);
  if (mode !== "mock") return null;
  return (
    <div role="alert" className="bg-red-700 px-4 py-2 text-center font-semibold text-white">
      MOCK MODE — not real results
    </div>
  );
}

const LARGE_TEXT_KEY = "secondshift_large_text";

function AppHeader() {
  const [largeText, setLargeText] = useState<boolean>(() => {
    try {
      return localStorage.getItem(LARGE_TEXT_KEY) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    document.documentElement.classList.toggle("large-text", largeText);
    try {
      localStorage.setItem(LARGE_TEXT_KEY, largeText ? "1" : "0");
    } catch {
      /* private mode: the toggle still applies for this session */
    }
  }, [largeText]);

  return (
    <header className="bg-[#1f3d2b] text-white">
      <div className="mx-auto flex max-w-md items-center justify-between gap-3 px-4 py-3">
        <span className="text-xl font-semibold tracking-tight">SecondShift</span>
        <button
          type="button"
          aria-pressed={largeText}
          onClick={() => setLargeText((v) => !v)}
          className="rounded border border-white/50 px-3 text-sm text-white"
        >
          Aa · Large text {largeText ? "on" : "off"}
        </button>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <MockBanner />
      <AppHeader />
      <div className="mx-auto w-full max-w-md pb-24">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/live" element={<LivePage />} />
          <Route path="/homes" element={<HomesPage />} />
          <Route path="/learn" element={<LearnPage />} />
          <Route path="/checkup/new" element={<CheckupNew />} />
          <Route path="/custom" element={<CustomPage />} />
          <Route path="/checkup/:id/processing" element={<Processing />} />
          <Route path="/checkup/:id/report" element={<ReportPage />} />
          <Route path="/checkup/:id/fixes" element={<Fixes />} />
          <Route path="/checkup/:id/recheck" element={<RecheckPage />} />
          <Route path="/rules" element={<RulesPage />} />
          <Route path="/watch/setup" element={<WatchSetup />} />
          <Route path="/camera" element={<CameraPage />} />
          <Route path="/watch/live" element={<WatchLive />} />
          <Route path="/ask" element={<AskPage />} />
          <Route path="/eval" element={<EvalPage />} />
          <Route path="/eval/label" element={<EvalLabelPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
        <Footer />
      </div>
      <TabBar />
    </BrowserRouter>
  );
}
