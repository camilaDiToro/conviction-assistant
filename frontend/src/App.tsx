import { Navigate, Route, Routes } from 'react-router-dom'
import LandingPage from './features/home/LandingPage'
import DesignLayout from './features/design/DesignLayout'
import OverviewPage from './features/design/OverviewPage'
import CorpusPage from './features/design/CorpusPage'
import ToolsPage from './features/design/ToolsPage'
import RetrievalPage from './features/design/RetrievalPage'
import VerifierPage from './features/design/VerifierPage'
import AgentLoopPage from './features/design/AgentLoopPage'
import ProvidersPage from './features/design/ProvidersPage'
import CostPage from './features/design/CostPage'
import LayeringPage from './features/design/LayeringPage'
import TiersPage from './features/design/TiersPage'
import ChatPage from './features/chat/ChatPage'
import AccessGate from './features/chat/AccessGate'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />

      <Route path="/design" element={<DesignLayout />}>
        <Route index element={<Navigate to="overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="pipeline/corpus" element={<CorpusPage />} />
        <Route path="pipeline/tools" element={<ToolsPage />} />
        <Route path="pipeline/retrieval" element={<RetrievalPage />} />
        <Route path="pipeline/verifier" element={<VerifierPage />} />
        <Route path="pipeline/agent-loop" element={<AgentLoopPage />} />
        <Route path="plumbing/providers" element={<ProvidersPage />} />
        <Route path="plumbing/cost" element={<CostPage />} />
        <Route path="plumbing/layering" element={<LayeringPage />} />
        <Route path="framing/tiers" element={<TiersPage />} />
      </Route>

      <Route
        path="/chat"
        element={
          <AccessGate>
            <ChatPage />
          </AccessGate>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
