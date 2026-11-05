import { Link, Route, Routes } from "react-router";
import { Layout } from "./components/Layout";
import { Card } from "./components/ui";
import { AccountDetailPage } from "./pages/AccountDetail";
import { AccountsPage } from "./pages/Accounts";
import { AlgorithmsPage } from "./pages/Algorithms";
import { InvestigationPage } from "./pages/Investigation";
import { LiveTransfersPage } from "./pages/LiveTransfers";
import { OverviewPage } from "./pages/Overview";
import { SimulatorPage } from "./pages/Simulator";
import { TransactionsPage } from "./pages/Transactions";

function NotFound() {
  return (
    <Card className="p-8 text-center">
      <h1 className="text-[22px] font-bold">Page not found</h1>
      <p className="mt-2 text-label-2">This address doesn't match any SecFlow view.</p>
      <Link to="/" className="mt-4 inline-block font-medium text-accent">Go to Overview</Link>
    </Card>
  );
}

export function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/live" element={<LiveTransfersPage />} />
        <Route path="/transactions" element={<TransactionsPage />} />
        <Route path="/accounts" element={<AccountsPage />} />
        <Route path="/accounts/:accountId" element={<AccountDetailPage />} />
        <Route path="/investigations/:requestId" element={<InvestigationPage />} />
        <Route path="/simulator" element={<SimulatorPage />} />
        <Route path="/algorithms" element={<AlgorithmsPage />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Layout>
  );
}
