import { Route, Routes } from 'react-router-dom';

import Layout from './components/Layout';
import AssistantPage from './pages/AssistantPage';
import ConversationsPage from './pages/ConversationsPage';
import MemoryPage from './pages/MemoryPage';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<AssistantPage />} />
        <Route path="/conversations" element={<ConversationsPage />} />
        <Route path="/memory" element={<MemoryPage />} />
        <Route path="*" element={<AssistantPage />} />
      </Routes>
    </Layout>
  );
}
