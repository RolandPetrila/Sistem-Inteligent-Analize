import { lazy, Suspense } from "react";
import { Routes, Route, Link } from "react-router-dom";
import Layout from "./components/Layout";

// Lazy-loaded pages for code splitting
const Dashboard = lazy(() => import("./pages/Dashboard"));
const NewAnalysis = lazy(() => import("./pages/NewAnalysis"));
const ReportsList = lazy(() => import("./pages/ReportsList"));
const Companies = lazy(() => import("./pages/Companies"));
const Settings = lazy(() => import("./pages/Settings"));
const AnalysisProgress = lazy(() => import("./pages/AnalysisProgress"));
const ReportView = lazy(() => import("./pages/ReportView"));
const CompareCompanies = lazy(() => import("./pages/CompareCompanies"));
const Monitoring = lazy(() => import("./pages/Monitoring"));
const BatchAnalysis = lazy(() => import("./pages/BatchAnalysis"));
const CompanyDetail = lazy(() => import("./pages/CompanyDetail"));

function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[40vh]">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary" />
    </div>
  );
}

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <h1 className="text-6xl font-bold text-gray-500 mb-4">404</h1>
      <p className="text-xl text-gray-400 mb-6">Pagina nu a fost gasita</p>
      <Link to="/" className="btn-primary px-6 py-2 rounded-lg">
        Inapoi la Dashboard
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/new-analysis" element={<NewAnalysis />} />
          <Route path="/analysis/:id" element={<AnalysisProgress />} />
          <Route path="/reports" element={<ReportsList />} />
          <Route path="/report/:id" element={<ReportView />} />
          <Route path="/companies" element={<Companies />} />
          <Route path="/company/:id" element={<CompanyDetail />} />
          <Route path="/compare" element={<CompareCompanies />} />
          <Route path="/monitoring" element={<Monitoring />} />
          <Route path="/batch" element={<BatchAnalysis />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
