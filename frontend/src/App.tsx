import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import Layout from './components/Layout';
import DashboardPage from './pages/DashboardPage';
import RecordsPage from './pages/RecordsPage';
import ScraperPage from './pages/ScraperPage';
import SchedulerPage from './pages/SchedulerPage';
import LogsPage from './pages/LogsPage';
import SettingsPage from './pages/SettingsPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/records/:dataType" element={<RecordsPage />} />
          <Route path="/records" element={<Navigate to="/records/part" replace />} />
          <Route path="/scraper" element={<ScraperPage />} />
          <Route path="/scheduler" element={<SchedulerPage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
