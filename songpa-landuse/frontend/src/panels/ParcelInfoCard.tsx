import { useAppStore } from '../store/useAppStore';

export default function ParcelInfoCard() {
  const { selectedParcel, setSelectedParcel } = useAppStore();

  if (!selectedParcel) return null;

  return (
    <div style={{
      position: 'absolute', top: 16, left: '50%', transform: 'translateX(-50%)',
      zIndex: 100, minWidth: 420, maxWidth: 600,
      background: 'rgba(15, 15, 35, 0.88)',
      backdropFilter: 'blur(16px)',
      borderRadius: 14, padding: '16px 20px',
      border: '1px solid rgba(255,255,255,0.1)',
      boxShadow: '0 12px 40px rgba(0,0,0,0.5)',
      color: '#e2e8f0',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 14, fontWeight: 700 }}>📍 필지 정보</span>
        <button onClick={() => setSelectedParcel(null)} style={{
          background: 'rgba(255,255,255,0.1)', border: 'none', color: '#94a3b8',
          width: 28, height: 28, borderRadius: '50%', cursor: 'pointer',
          fontSize: 14, display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: 'background 0.2s',
        }}>✕</button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 16px', fontSize: 13 }}>
        <div>
          <span style={{ color: '#64748b', fontSize: 11 }}>PNU</span>
          <div style={{ fontWeight: 600, fontFamily: 'monospace', fontSize: 12, marginTop: 2 }}>{selectedParcel.PNU}</div>
        </div>
        <div>
          <span style={{ color: '#64748b', fontSize: 11 }}>주소 (지번)</span>
          <div style={{ fontWeight: 500, marginTop: 2 }}>{selectedParcel.JIBUN || '-'}</div>
        </div>
        <div>
          <span style={{ color: '#64748b', fontSize: 11 }}>용도지역</span>
          <div style={{ fontWeight: 500, marginTop: 2, color: '#818cf8' }}>{selectedParcel.zone_norm}</div>
        </div>
        <div>
          <span style={{ color: '#64748b', fontSize: 11 }}>주용도</span>
          <div style={{ fontWeight: 500, marginTop: 2, color: '#f59e0b' }}>{selectedParcel.main_purpose}</div>
        </div>
        <div>
          <span style={{ color: '#64748b', fontSize: 11 }}>대지면적</span>
          <div style={{ fontWeight: 600, marginTop: 2 }}>{Math.round(selectedParcel.area_m2).toLocaleString()} ㎡</div>
        </div>
      </div>
    </div>
  );
}
