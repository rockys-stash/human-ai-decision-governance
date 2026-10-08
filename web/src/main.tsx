import "@fontsource/geist-sans/400.css";
import "@fontsource/geist-sans/500.css";
import "@fontsource/geist-sans/600.css";
import "@fontsource/geist-mono/400.css";
import "@fontsource/geist-mono/500.css";
import "./styles.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { LiveProvider } from "./lib/live";
import { ReviewerProvider } from "./lib/reviewer";
import { Audit } from "./pages/Audit";
import { Calibration } from "./pages/Calibration";
import { Experiments } from "./pages/Experiments";
import { Method } from "./pages/Method";
import { NotFound } from "./pages/NotFound";
import { Policy } from "./pages/Policy";
import { Queue } from "./pages/Queue";

const root = document.getElementById("root");
if (!root) throw new Error("missing #root element");

createRoot(root).render(
  <StrictMode>
    <ReviewerProvider>
      <LiveProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Navigate to="/queue" replace />} />
              <Route path="queue" element={<Queue />} />
              <Route path="queue/:caseId" element={<Queue />} />
              <Route path="audit" element={<Audit />} />
              <Route path="policy" element={<Policy />} />
              <Route path="experiments" element={<Experiments />} />
              <Route path="calibration" element={<Calibration />} />
              <Route path="method" element={<Method />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </LiveProvider>
    </ReviewerProvider>
  </StrictMode>,
);
