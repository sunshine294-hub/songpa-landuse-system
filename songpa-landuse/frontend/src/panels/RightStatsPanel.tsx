import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { useAppStore } from '../store/useAppStore';
import { PURPOSE_COLORS, ZONE_COLORS } from '../constants/palette';

interface StatsData {
  summary: { parcel_count: number; building_count: number; total_area_m2: number; emd_count: number; oa_count?: number };
  by_purpose: { key: string; parcels: number; area_m2: number; pct: number }[];
  by_zone: { key: string; parcels: number; area_m2: number; pct: number }[];
  by_emd_purpose: { emd: string; purpose: string; parcels: number; area_m2: number }[];
  oa_totals: { population: number; households: number };
}

const TABS = ['건축물 주용도', '용도지역', '지적 및 동별 분석', '집계구 통계'];

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
        <Tooltip formatter={(v: any) => `${Number(v || 0).toLocaleString()} ㎡`} contentStyle={{
          background: '#1e293b', border: 'none', borderRadius: 8, color: '#e2e8f0', fontSize: 12,
        }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

function DataTable({ data }: { data: { key: string; parcels: number; area_m2: number; pct: number }[] }) {
  return (
    <div style={{ overflowY: 'auto', maxHeight: 220, border: '1px solid #f1f5f9', borderRadius: 8 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e2e8f0', position: 'sticky', top: 0, background: '#fff', zIndex: 1 }}>
            <th style={{ padding: '6px 4px', textAlign: 'left', fontWeight: 600, color: '#64748b' }}>구분</th>
            <th style={{ padding: '6px 4px', textAlign: 'right', fontWeight: 600, color: '#64748b' }}>필지수</th>
            <th style={{ padding: '6px 4px', textAlign: 'right', fontWeight: 600, color: '#64748b' }}>면적(㎡)</th>
            <th style={{ padding: '6px 4px', textAlign: 'right', fontWeight: 600, color: '#64748b' }}>비율(%)</th>
          </tr>
        </thead>
        <tbody>
          {data.map((d) => (
            <tr key={d.key} style={{ borderBottom: '1px solid #f1f5f9' }}>
              <td style={{ padding: '5px 4px', color: '#334155', fontWeight: 500 }}>{d.key}</td>
              <td style={{ padding: '5px 4px', textAlign: 'right', color: '#475569' }}>{d.parcels.toLocaleString()}</td>
              <td style={{ padding: '5px 4px', textAlign: 'right', color: '#475569' }}>{Math.round(d.area_m2).toLocaleString()}</td>
              <td style={{ padding: '5px 4px', textAlign: 'right', color: '#6366f1', fontWeight: 600 }}>{d.pct.toFixed(1)}</td>
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
  const [selectedEmd, setSelectedEmd] = useState<string>('');

  useEffect(() => {
    fetch('data/stats.json').then(r => r.json()).then(data => {
      setStats(data);
      if (data.by_emd_purpose && data.by_emd_purpose.length > 0) {
        const uniqueEmds = Array.from(new Set(data.by_emd_purpose.map((d: any) => d.emd))) as string[];
        if (uniqueEmds.length > 0) {
          // 가급적 실제 동이름이 먼저 선택되게 함
          const validEmd = uniqueEmds.find(e => e !== '알수없음' && e !== '') || uniqueEmds[0];
          setSelectedEmd(validEmd);
        }
      }
    }).catch(() => {});
  }, []);

  if (!stats) {
    return (
      <aside style={{ width: 360, minWidth: 360, background: '#fff', borderLeft: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
        데이터 로딩...
      </aside>
    );
  }

  // 행정동 목록 추출
  const emdList = Array.from(new Set(stats.by_emd_purpose.map(d => d.emd))).filter(Boolean) as string[];

  // 선택된 행정동의 주용도 데이터 가공
  const emdPurposeData = stats.by_emd_purpose.filter(d => d.emd === selectedEmd);
  const emdTotalArea = emdPurposeData.reduce((acc, curr) => acc + curr.area_m2, 0);
  const formattedEmdData = emdPurposeData.map(d => ({
    key: d.purpose,
    parcels: d.parcels,
    area_m2: d.area_m2,
    pct: emdTotalArea > 0 ? (d.area_m2 / emdTotalArea * 100) : 0,
  })).sort((a, b) => b.area_m2 - a.area_m2);

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
            flex: 1, padding: '10px 2px', border: 'none', cursor: 'pointer',
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Overview cards */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div style={{ textAlign: 'center', padding: '12px 8px', background: '#f8fafc', borderRadius: 8, border: '1px solid #f1f5f9' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#6366f1' }}>{stats.summary.emd_count}</div>
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>법정동 수</div>
              </div>
              <div style={{ textAlign: 'center', padding: '12px 8px', background: '#f8fafc', borderRadius: 8, border: '1px solid #f1f5f9' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#1e293b' }}>
                  {(stats.summary.total_area_m2 / 1e6).toFixed(1)}
                </div>
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>총면적 (k㎡)</div>
              </div>
            </div>

            {/* EMD Land Use Cross-analysis (by_emd_purpose) */}
            <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#1e293b' }}>📍 행정동별 주용도 상세 분석</span>
                <select 
                  value={selectedEmd} 
                  onChange={(e) => setSelectedEmd(e.target.value)}
                  style={{
                    padding: '4px 8px', borderRadius: 6, border: '1px solid #cbd5e1', 
                    fontSize: 12, outline: 'none', background: '#fff', color: '#334155'
                  }}
                >
                  {emdList.map(emd => (
                    <option key={emd} value={emd}>{emd}</option>
                  ))}
                </select>
              </div>

              {formattedEmdData.length > 0 ? (
                <>
                  <DonutChart data={formattedEmdData} colors={PURPOSE_COLORS} />
                  <DataTable data={formattedEmdData} />
                </>
              ) : (
                <div style={{ textAlign: 'center', color: '#94a3b8', fontSize: 12, padding: '20px 0' }}>
                  해당 행정동의 분석 데이터가 없습니다.
                </div>
              )}
            </div>
          </div>
        )}
        {activeTab === 3 && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
              <div style={{ textAlign: 'center', padding: '16px 8px', background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)', borderRadius: 12 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#1e40af' }}>
                  {stats.oa_totals.population.toLocaleString()}
                </div>
                <div style={{ fontSize: 11, color: '#3b82f6', marginTop: 4 }}>👥 총인구</div>
              </div>
              <div style={{ textAlign: 'center', padding: '16px 8px', background: 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)', borderRadius: 12 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#166534' }}>
                  {stats.oa_totals.households.toLocaleString()}
                </div>
                <div style={{ fontSize: 11, color: '#22c55e', marginTop: 4 }}>🏠 총가구</div>
              </div>
            </div>
            <div style={{ fontSize: 12, color: '#64748b', textAlign: 'center', background: '#f8fafc', padding: 12, borderRadius: 8, border: '1px solid #f1f5f9' }}>
              💡 집계구 <b>{(stats.summary.oa_count || 1278).toLocaleString()}</b>개 기준 · 2024년 통계
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
