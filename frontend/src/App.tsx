import { useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Footer from "./components/Footer";
import AskPage from "./pages/AskPage";
import CameraPage from "./pages/CameraPage";
import CheckupNew from "./pages/CheckupNew";
import EvalLabelPage from "./pages/EvalLabelPage";
import EvalPage from "./pages/EvalPage";
import Fixes from "./pages/Fixes";
import Home from "./pages/Home";
import Processing from "./pages/Processing";
import RecheckPage from "./pages/RecheckPage";
import ReportPage from "./pages/ReportPage";
import RulesPage from "./pages/RulesPage";
import SettingsPage from "./pages/SettingsPage";
import WatchLive from "./pages/WatchLive";
import WatchSetup from "./pages/WatchSetup";

/** Route table - every route in spec section 13 exists from Phase 0. */

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

export default function App() {
  return (
    <BrowserRouter>
      <MockBanner />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/checkup/new" element={<CheckupNew />} />
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
    </BrowserRouter>
  );
}
