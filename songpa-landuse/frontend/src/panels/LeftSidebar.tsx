import { useAppStore } from '../store/useAppStore';
import { PURPOSE_COLORS, ZONE_COLORS } from '../constants/palette';

const LAYER_ITEMS: { key: keyof ReturnType<typeof useAppStore.getState>['layers']; label: string; icon: string }[] = [
  { key: 'emdBorder', label: '행정동 경계', icon: '🗺️' },
  { key: 'emdLabel', label: '행정동 이름', icon: '🏷️' },
  { key: 'oaStats', label: '집계구 통계', icon: '📊' },
  { key: 'parcel', label: '필지', icon: '📐' },
  { key: 'building', label: '건축물', icon: '🏢' },
];

export default function LeftSidebar() {
  const { layers, toggleLayer, colorMode, setColorMode } = useAppStore();
  const colors = colorMode === 'purpose' ? PURPOSE_COLORS : ZONE_COLORS;

  return (
    <aside style={{
      width: 280, minWidth: 280, height: '100%',
      background: 'linear-gradient(180deg, #0f0f23 0%, #1a1a3e 100%)',
      color: '#e2e8f0', display: 'flex', flexDirection: 'column',
      borderRight: '1px solid rgba(255,255,255,0.06)',
    }}>
      {/* Header */}
      <div style={{
        padding: '20px 20px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <h1 style={{ fontSize: 16, fontWeight: 700, letterSpacing: -0.3, margin: 0 }}>
          🏙️ 송파구 토지이용
        </h1>
        <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>인구 분석 시스템</p>
      </div>

      {/* Layer toggles */}
      <div style={{ padding: 16, flex: 1, overflowY: 'auto' }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
          레이어
        </div>
        {LAYER_ITEMS.map(({ key, label, icon }) => (
          <label key={key} style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px',
            borderRadius: 8, cursor: 'pointer', marginBottom: 4,
            background: layers[key] ? 'rgba(99,102,241,0.12)' : 'transparent',
            transition: 'background 0.2s',
          }}>
            <span style={{ fontSize: 16 }}>{icon}</span>
            <span style={{ flex: 1, fontSize: 13, fontWeight: 500 }}>{label}</span>
            <div onClick={(e) => { e.preventDefault(); toggleLayer(key); }} style={{
              width: 40, height: 22, borderRadius: 11, cursor: 'pointer',
              background: layers[key] ? '#6366f1' : '#374151',
              transition: 'background 0.2s', position: 'relative',
            }}>
              <div style={{
                width: 16, height: 16, borderRadius: '50%', background: '#fff',
                position: 'absolute', top: 3,
                left: layers[key] ? 21 : 3, transition: 'left 0.2s',
              }} />
            </div>
          </label>
        ))}

        {/* Color mode toggle */}
        <div style={{ marginTop: 20, fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
          필지 색상 기준
        </div>
        <div style={{ display: 'flex', gap: 4, background: 'rgba(255,255,255,0.05)', borderRadius: 8, padding: 3 }}>
          {(['purpose', 'zone'] as const).map((m) => (
            <button key={m} onClick={() => setColorMode(m)} style={{
              flex: 1, padding: '8px 0', border: 'none', borderRadius: 6,
              cursor: 'pointer', fontSize: 12, fontWeight: 600,
              color: colorMode === m ? '#fff' : '#94a3b8',
              background: colorMode === m ? '#6366f1' : 'transparent',
              transition: 'all 0.2s',
            }}>
              {m === 'purpose' ? '주용도' : '용도지역'}
            </button>
          ))}
        </div>

        {/* Legend */}
        <div style={{ marginTop: 20, fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>
          범례
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {Object.entries(colors).map(([label, color]) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
              <div style={{ width: 14, height: 14, borderRadius: 3, background: color, flexShrink: 0, border: '1px solid rgba(255,255,255,0.1)' }} />
              <span style={{ color: '#cbd5e1' }}>{label}</span>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
