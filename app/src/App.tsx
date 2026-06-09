import { HashRouter, Routes, Route } from 'react-router-dom';

import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import WikiBrowser from './pages/WikiBrowser';
import WikiPage from './pages/WikiPage';
import Ingest from './pages/Ingest';

function App() {
  return (
    <HashRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/ingest" element={<Ingest />} />
          <Route path="/wiki" element={<WikiBrowser />} />
          <Route path="/wiki/:slug" element={<WikiPage />} />
        </Routes>
      </Layout>
    </HashRouter>
  );
}

export default App;
