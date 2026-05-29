import LeftSidebar from './panels/LeftSidebar';
import MapView from './map/MapView';
import RightStatsPanel from './panels/RightStatsPanel';
import ParcelInfoCard from './panels/ParcelInfoCard';

export default function App() {
  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh' }}>
      <LeftSidebar />
      <div style={{ flex: 1, position: 'relative' }}>
        <MapView />
        <ParcelInfoCard />
      </div>
      <RightStatsPanel />
    </div>
  );
}
