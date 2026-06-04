import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import DashboardPage from './pages/DashboardPage';
import VdotPage from './pages/VdotPage';
import TrainingLoadPage from './pages/TrainingLoadPage';
import ActivitiesPage from './pages/ActivitiesPage';
import ActivityDetailPage from './pages/ActivityDetailPage';
import BodySignalsPage from './pages/BodySignalsPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/vdot" element={<VdotPage />} />
          <Route path="/training-load" element={<TrainingLoadPage />} />
          <Route path="/activities" element={<ActivitiesPage />} />
          <Route path="/activities/:id" element={<ActivityDetailPage />} />
          <Route path="/body-signals" element={<BodySignalsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
