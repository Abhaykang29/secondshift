import { useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ScanEye, Type } from "lucide-react";
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
import ComparePage from "./pages/ComparePage";
import RecheckPage from "./pages/RecheckPage";
import ReportPage from "./pages/ReportPage";
import RulesPage from "./pages/RulesPage";
import SettingsPage from "./pages/SettingsPage";
import WatchLive from "./pages/WatchLive";
import WatchSetup from "./pages/WatchSetup";

/**
 * App shell (redesign spec 4): 56px surface header with the wordmark,
 * content column (max 1120px on desktop), bottom tab bar. Every
 * pre-PWA route stays reachable - the tab pages link into the flows.
 */

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
    <header className="sticky top-0 z-40 bg-surface shadow-bar">
      <div className="mx-auto flex h-14 w-full max-w-[1120px] items-center justify-between px-4">
        <span className="flex items-center gap-2.5">
          <span
            className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-accent text-text-inverse"
            aria-hidden
          >
            <ScanEye size={18} strokeWidth={2.25} />
          </span>
          <span className="text-[22px] font-extrabold leading-none tracking-[-0.035em] text-accent">
            SecondShift
          </span>
        </span>
        <button
          type="button"
          aria-label="Large text"
          aria-pressed={largeText}
          onClick={() => setLargeText((v) => !v)}
          className={`inline-flex h-10 w-10 items-center justify-center rounded-full transition-colors duration-[120ms] ${
            largeText
              ? "bg-accent-bg text-accent hover:bg-accent-bg-hover"
              : "bg-surface-3 text-text hover:bg-surface-3-hover"
          }`}
        >
          <Type size={19} strokeWidth={2} aria-hidden />
        </button>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppHeader />
      <div className="mx-auto w-full max-w-[1120px] px-3 pb-28 pt-4 sm:px-4">
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
          <Route path="/compare/:beforeId/:afterId" element={<ComparePage />} />
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
