import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { useAppStore } from '../store/useAppStore';
import { PURPOSE_COLORS, ZONE_COLORS } from '../constants/palette';

interface StatsData {
  summary: { parcel_count: number; building_count: number; total_area_m2: number; emd_count: number };
  by_purpose: { key: string; parcels: number; area_m2: number; pct: number }[];
  by_zone: { key: string; parcels: number; area_m2: number; pct: number }[];
  by_emd_purpose: { emd: string; purpose: string; parcels: number; area_m2: number }[];
  oa_totals: { population: number; households: number };
}

const TABS = ['건축물 주용도', '용도지역', '지적', '집계구 통계'];

function DonutChart({ data, colors }: { data: { key: string; parcels: number; area_m2: number; pct: number }[]; colors: Record<string, string> }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={data} dataKey="area_m2" nameKey="key" cx="50%" cy="50%" innerRadius={55} outerRadius={90}
          paddingAngle={1} stroke="none">
          {data.map((d) => (
            <Cell key={d.key} fill={colors[d.key] || '#BDC3C7'} />
          ))}
        </Pie>
        <Tooltip formatter={(v: number) => `${v.toLocaleString()} ㎡`} contentStyle={{
          background: '#1e293b', border: 'none', borderRadius: 8, color: '#e2e8f0', fontSize: 12,
        }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

function DataTable({ data }: { data: { key: string; parcels: number; area_m2: number; pct: number }[] }) {
  return (
    <div style={{ overflowY: 'auto', maxHeight: 300 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e2e8f0', position: 'sticky', top: 0, background: '#fff' }}>
            <th style={{ padding: '8px 6px', textAlign: 'left', fontWeight: 600 }}>구분</th>
            <th style={{ padding: '8px 6px', textAlign: 'right', fontWeight: 600 }}>필지수</th>
            <th style={{ padding: '8px 6px', textAlign: 'right', fontWeight: 600 }}>면적(㎡)</th>
            <th style={{ padding: '8px 6px', textAlign: 'right', fontWeight: 600 }}>비율(%)</th>
          </tr>
        </thead>
        <tbody>
          {data.map((d) => (
            <tr key={d.key} style={{ borderBottom: '1px solid #f1f5f9' }}>
              <td style={{ padding: '7px 6px', color: '#334155' }}>{d.key}</td>
              <td style={{ padding: '7px 6px', textAlign: 'right', color: '#475569' }}>{d.parcels.toLocaleString()}</td>
              <td style={{ padding: '7px 6px', textAlign: 'right', color: '#475569' }}>{Math.round(d.area_m2).toLocaleString()}</td>
              <td style={{ padding: '7px 6px', textAlign: 'right', color: '#6366f1', fontWeight: 600 }}>{d.pct.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function RightStatsPanel() {
  const { activeTab, setActiveTab } = useAppStore();
  const [stats, setStats] = useState<StatsData | null>(null);

  useEffect(() => {
    fetch('/data/stats.json').then(r => r.json()).then(setStats).catch(() => {});
  }, []);

  if (!stats) {
    return (
      <aside style={{ width: 360, minWidth: 360, background: '#fff', borderLeft: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
        데이터 로딩...
      </aside>
    );
  }

  return (
    <aside style={{
      width: 360, minWidth: 360, height: '100%', background: '#fff',
      borderLeft: '1px solid #e5e7eb', display: 'flex', flexDirection: 'column',
      overflowY: 'auto',
    }}>
      {/* Summary cards */}
      <div style={{ padding: 16, borderBottom: '1px solid #f1f5f9' }}>
        <h2 style={{ fontSize: 15, fontWeight: 700, color: '#1e293b', margin: '0 0 12px' }}>📊 송파구 통계</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          {[
            { label: '총 필지', value: stats.summary.parcel_count.toLocaleString(), icon: '📐' },
            { label: '건물 매칭', value: stats.summary.building_count.toLocaleString(), icon: '🏢' },
            { label: '총 인구', value: stats.oa_totals.population.toLocaleString(), icon: '👥' },
            { label: '총 가구', value: stats.oa_totals.households.toLocaleString(), icon: '🏠' },
          ].map((c) => (
            <div key={c.label} style={{
              padding: '10px 12px', borderRadius: 8,
              background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
              border: '1px solid #e2e8f0',
            }}>
              <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>{c.icon} {c.label}</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#1e293b' }}>{c.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid #e5e7eb', flexShrink: 0 }}>
        {TABS.map((t, i) => (
          <button key={t} onClick={() => setActiveTab(i)} style={{
            flex: 1, padding: '10px 4px', border: 'none', cursor: 'pointer',
            fontSize: 11, fontWeight: 600, background: 'transparent',
            color: activeTab === i ? '#6366f1' : '#94a3b8',
            borderBottom: activeTab === i ? '2px solid #6366f1' : '2px solid transparent',
            transition: 'all 0.2s',
          }}>
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        {activeTab === 0 && (
          <>
            <DonutChart data={stats.by_purpose} colors={PURPOSE_COLORS} />
            <DataTable data={stats.by_purpose} />
          </>
        )}
        {activeTab === 1 && (
          <>
            <DonutChart data={stats.by_zone} colors={ZONE_COLORS} />
            <DataTable data={stats.by_zone} />
          </>
        )}
        {activeTab === 2 && (
          <div>
            <div style={{ textAlign: 'center', padding: 20 }}>
              <div style={{ fontSize: 36, fontWeight: 700, color: '#6366f1' }}>
                {stats.summary.parcel_count.toLocaleString()}
              </div>
              <div style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>총 필지 수</div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, padding: '0 8px' }}>
              <div style={{ textAlign: 'center', padding: 16, background: '#f8fafc', borderRadius: 8 }}>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#1e293b' }}>{stats.summary.emd_count}</div>
                <div style={{ fontSize: 11, color: '#64748b' }}>법정동</div>
              </div>
              <div style={{ textAlign: 'center', padding: 16, background: '#f8fafc', borderRadius: 8 }}>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#1e293b' }}>
                  {(stats.summary.total_area_m2 / 1e6).toFixed(1)}
                </div>
                <div style={{ fontSize: 11, color: '#64748b' }}>총면적 (k㎡)</div>
              </div>
            </div>
          </div>
        )}
        {activeTab === 3 && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
              <div style={{ textAlign: 'center', padding: 20, background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)', borderRadius: 12 }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#1e40af' }}>
                  {stats.oa_totals.population.toLocaleString()}
                </div>
                <div style={{ fontSize: 12, color: '#3b82f6', marginTop: 4 }}>👥 총인구</div>
              </div>
              <div style={{ textAlign: 'center', padding: 20, background: 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)', borderRadius: 12 }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#166534' }}>
                  {stats.oa_totals.households.toLocaleString()}
                </div>
                <div style={{ fontSize: 12, color: '#22c55e', marginTop: 4 }}>🏠 총가구</div>
              </div>
            </div>
            <div style={{ fontSize: 12, color: '#64748b', textAlign: 'center' }}>
              집계구 {1278}개 기준 · 2024년
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
