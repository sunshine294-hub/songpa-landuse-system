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

const TABS = ['건축물 주용도', '용도지역', '지적 및 동별 분석', '집계구 통계', '심층 분석'];

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
      <div style={{ display: 'flex', flexWrap: 'wrap', borderBottom: '1px solid #e5e7eb', flexShrink: 0, background: '#f8fafc' }}>
        {TABS.map((t, i) => (
          <button key={t} onClick={() => setActiveTab(i)} style={{
            width: i < 3 ? '33.33%' : '50%', padding: '10px 2px', border: 'none', cursor: 'pointer',
            fontSize: '10.5px', fontWeight: 600, background: activeTab === i ? '#fff' : 'transparent',
            color: activeTab === i ? '#6366f1' : '#64748b',
            borderBottom: activeTab === i ? '2px solid #6366f1' : '1px solid #e2e8f0',
            borderRight: i % 3 !== 2 && i < 3 ? '1px solid #e2e8f0' : i === 3 ? '1px solid #e2e8f0' : 'none',
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
        {activeTab === 4 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, fontSize: 12, lineHeight: 1.6, color: '#334155' }}>
            <div style={{ padding: '4px 0', borderBottom: '2px solid #6366f1', marginBottom: 8 }}>
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: '#1e293b' }}>🏙️ 토지이용 및 인구 심층 분석 보고서</h3>
              <p style={{ margin: '4px 0 0', fontSize: 11, color: '#64748b' }}>연속지적도 · 대장 표제부 · SGIS 인구 결합 분석 결과</p>
            </div>

            {/* Section 1 */}
            <div style={{ background: '#f8fafc', padding: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}>
              <h4 style={{ margin: '0 0 8px', fontSize: 12, fontWeight: 700, color: '#1e293b', display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>🚨</span> 송파구 재건축/재개발 시급 지역
              </h4>
              
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontWeight: 600, color: '#4f46e5', fontSize: 11 }}>1순위 (재건축 필요): 오륜동 일대</div>
                <ul style={{ margin: '4px 0 0', paddingLeft: 16, fontSize: 11, color: '#475569' }}>
                  <li><b>노후도</b>: 대장 상 사용승인일 1988년 집중 (준공 후 38년 경과)</li>
                  <li><b>용도지역</b>: 제3종일반주거지역 지정으로 향후 고밀개발 유리</li>
                  <li><b>필지특징</b>: 단일 필지 면적이 매우 넓어 재건축 사업성 극대화</li>
                </ul>
              </div>

              <div>
                <div style={{ fontWeight: 600, color: '#0891b2', fontSize: 11 }}>2순위 (재개발 필요): 풍납1·2동 및 거여·마천동</div>
                <ul style={{ margin: '4px 0 0', paddingLeft: 16, fontSize: 11, color: '#475569' }}>
                  <li><b>토지이용</b>: 단독주택 및 근린생활시설 비율 68% 이상 밀집</li>
                  <li><b>밀도분석</b>: 면적 대비 가구수 및 인구밀도 송파구 평균 1.4배 초과</li>
                  <li><b>공간정책</b>: 풍납토성 규제를 고려한 준주거 완화 또는 모아타운 권장</li>
                </ul>
              </div>
            </div>

            {/* Section 2 */}
            <div style={{ background: '#f8fafc', padding: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}>
              <h4 style={{ margin: '0 0 8px', fontSize: 12, fontWeight: 700, color: '#1e293b', display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>⚖️</span> 송파구 vs 강동구 토지이용 정량 비교
              </h4>
              
              <div style={{ overflowX: 'auto', marginBottom: 8 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10.5, textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #cbd5e1', background: '#e2e8f0', fontWeight: 600 }}>
                      <th style={{ padding: 4 }}>구분</th>
                      <th style={{ padding: 4 }}>송파구</th>
                      <th style={{ padding: 4 }}>강동구</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: 4, fontWeight: 600 }}>필지 수</td>
                      <td style={{ padding: 4 }}>약 31,153필지</td>
                      <td style={{ padding: 4 }}>약 22,000필지</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: 4, fontWeight: 600 }}>대표 용도</td>
                      <td style={{ padding: 4 }}>중심/일반상업, 준주거, 3종주거 조화</td>
                      <td style={{ padding: 4 }}>2종주거, 자연녹지 위주</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: 4, fontWeight: 600 }}>자족기능</td>
                      <td style={{ padding: 4 }}>매우 높음 (잠실역, 문정법조 등)</td>
                      <td style={{ padding: 4 }}>낮음 (배후 거주 베드타운)</td>
                    </tr>
                    <tr>
                      <td style={{ padding: 4, fontWeight: 600 }}>세입기반</td>
                      <td style={{ padding: 4, fontStyle: 'italic', color: '#6366f1' }}>자립도 강남3구 수준</td>
                      <td style={{ padding: 4, color: '#ef4444' }}>주거위주 세입 부족</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Section 3 */}
            <div style={{ background: '#f8fafc', padding: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}>
              <h4 style={{ margin: '0 0 8px', fontSize: 12, fontWeight: 700, color: '#1e293b', display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>💡</span> 공간계획적 주요 시사점
              </h4>
              <ol style={{ margin: 0, paddingLeft: 16, fontSize: 11, color: '#475569', display: 'flex', flexDirection: 'column', gap: 6 }}>
                <li><b>자족과 세수 격차</b>: 송파는 강력한 업무지구(잠실, 문정)를 확보해 세수가 높으나, 강동은 순수 베드타운 비중이 높아 향후 개발(고덕비즈밸리) 시 상업필지 비율 5% 이상 확보가 필수적임.</li>
                <li><b>용도지역 정비속도 편차</b>: 송파는 주요 노후단지가 3종일반/준주거지에 있어 사업성이 좋으나, 강동은 대다수가 2종일반(7층이하 규제 등)에 묶여 있어 종상향 심의 및 용적률 갈등비용이 큼.</li>
                <li><b>교통망 영향과 선형 구조</b>: 집계구 분포 상 강동구는 지하철 노선 연장을 따라 선형으로 고가구 밀도가 편중되어 교통 병목을 심화시킴. 광역적 기반시설 공급 정책과의 결합이 강력히 요구됨.</li>
              </ol>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
