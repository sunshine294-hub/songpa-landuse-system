# 송파구 토지이용·인구 분석 시스템 구축 계획서

> 본 문서는 **코드 작성 AI 에이전트(바이브코딩)** 가 그대로 읽고 구현에 착수할 수 있도록 작성된 단일 명세서다.
> 모호한 결정은 모두 본 문서에서 사전에 확정해두었다. **"추천"·"검토 필요" 문구가 없도록** 의사결정을 박아두었으니, 에이전트는 이 문서를 진실 공급원(single source of truth)으로 삼고 구현하라.

---

## 0. 시스템 정의 (변경 금지)

1. **필지(parcel) 단위** 로 다음 두 속성을 지도에 표출하고, 사이드 패널에서 통계표·도넛차트로 도출한다.
   - 건축물의 **주용도(主用途)**  ← 건축물대장 표제부
   - **용도지역(用途地域)**  ← 토지특성정보(또는 토지이용계획)
2. **집계구(output area, OA) 단위** 로 다음 두 지표를 코로플레스 + 호버 툴팁으로 표출한다.
   - 총인구수
   - 가구수
3. 공간범위: **서울특별시 송파구**(법정동 시군구코드 `11710`)
4. 시간범위: **각 데이터셋의 최신 기준월**(시계열 분석 없음, 단일 스냅샷)
5. 표출 화면 구성은 강의자료 8쪽 참고 레퍼런스를 따른다:
   - 좌측 사이드바: 레이어 토글(행정동 경계 / 이름 라벨 / 집계구 통계 / 필지 / 건축물 주용도), 색상 범례
   - 우측 패널: 송파구 통계(건축물 주용도 / 용도지역 / 지적 / 집계구) 4탭, 도넛차트 + 표
   - 필지 클릭 시: 상단 카드에 PNU, 용도지역, 주용도, 주소, 지목·대지면적 표시

---

## 1. 데이터 필터링 결과 — "꼭 필요한 것"

사용자가 제시한 33종 중 **시스템 정의를 충족하는 데 실제로 필요한 데이터**는 다음 7종이다. 나머지는 모두 본 프로젝트에서 **사용하지 않는다**(다운로드 금지·전처리 대상 제외). 비고에 배제 사유를 명시한다.

### 1.1 필수 데이터 (총 7종 — ★ 표시는 사용자 리스트 외 추가 수집 필요)

| # | 데이터명 | 제공처 | 사용 목적 | 핵심 컬럼 |
|---|----------|--------|-----------|-----------|
| 1 | 행정구역(행정동 경계) | 브이월드 | 송파구 27개 행정동 경계, 라벨 | `EMD_CD`, `EMD_KOR_NM`, geometry |
| 2 | 연속지적도 | 브이월드 | 필지 폴리곤(약 31,153필지) 기본 도형 | `PNU`(19자리), `JIBUN`, geometry |
| 4 | 토지특성정보 | 브이월드 | **용도지역**(`LAND_USE_SITUATION` / `SPCFC_USE_AREA_NM`) | `PNU`, `용도지역명`, `지목`, `대지면적` |
| 7 | GIS건물통합정보 | 브이월드 | 건축물 폴리곤, 건물-필지 공간조인 보조 | `BD_MGT_SN`, `PNU`, `BULD_NM`, geometry |
| 8 | 건축물대장(표제부) | 건축HUB | **주용도**(`MAIN_PURPS_CD_NM`), 연면적, 층수 | `MGM_BLDRGST_PK`, `PLAT_PLC`, `MAIN_PURPS_CD_NM` |
| 9 | 건축물대장(부속지번) | 건축HUB | 1건물-N필지 매핑 해소 | `MGM_BLDRGST_PK`, `PNU` |
| ★ | **집계구 경계 + 인구/가구 통계** | **SGIS(통계청)** | 집계구 폴리곤·총인구·가구수 표출 | `TOT_REG_CD`(집계구코드), `TOT_PPLTN`, `TOT_HSHLD` |

★ **집계구 데이터는 사용자가 제시한 33종 리스트에 없으므로 별도 수집해야 한다.** 다운로드 경로는 §2.7 참고.

### 1.2 본 시스템에서 사용하지 않는 데이터 (28종)

| # | 데이터명 | 제외 사유 |
|---|----------|-----------|
| 3 | 토지임야정보 | 지목은 토지특성정보(#4)에 이미 포함 — 중복 |
| 5 | 개별공시지가 | 표출 항목 아님(주용도·용도지역만 표출) |
| 6 | 표준지공시지가 | 동일 |
| 10 | 연속주제도 | 용도지역은 #4로 대체 — 동일 데이터 중복 |
| 11 | 개발행위허가 | 표출 항목 아님 |
| 12 | 도시계획시설번호 | 참고용, 표출 항목 아님 |
| 13 | 수치지형도 1:5,000 | 베이스맵은 Vworld WMTS로 대체 |
| 14 | 임상도 | 송파구 산림 비중 낮음, 표출 항목 아님 |
| 15 | 생태자연도 | 동일 |
| 16 | 토지피복도 | 동일 |
| 17 | 국토환경성평가등급도 | 동일 |
| 18 | 택지정보(지구경계) | 송파구 위례 일부 외 영향 미미 |
| 19 | 택지정보(토지이용계획) | 동일 |
| 20 | 산업단지정보(경계) | **송파구에는 산업단지 없음** |
| 21 | 산업단지정보(토지이용계획) | 동일 |
| 22 | 생활권 | 도시기본계획 단위 — 본 시스템 단위(필지·집계구) 불일치 |
| 23 | 인구배분계획/시가화예정용지 | 동일 |
| 24 | 인구지표/도시경제·환경지표 | 본 시스템 인구지표는 집계구 #★ 사용 |
| 25 | 기상기후 | 표출 항목 아님 |
| 26 | 수리수문 | 동일 |
| 27~30 | 문화재 4종 | 참고용, 표출 항목 아님 |
| 31 | 백두대간보호지역 | **송파구 비대상** |
| 32 | 정맥보호지역 | **송파구 비대상** |
| 33 | 산사태위험지도 | 본 시스템 정의 외 |

### 1.3 추가로 필요한 데이터(사용자에게 알릴 항목)

다음 3종은 사용자 리스트 외이며 별도 발급/다운로드가 필요하다.

1. **SGIS 집계구 경계 SHP** (송파구) — `https://sgis.kostat.go.kr/view/pss/openDataIntrcn`
2. **SGIS 집계구별 총인구·가구수 통계 CSV** — 동일 포털, 인구·가구 항목
3. **Vworld 인증 API Key** (WMTS 베이스맵) — `https://www.vworld.kr/dev/v4apiRefer.do`

---

## 2. 데이터 단위 통합 규칙 (전처리 시 반드시 준수)

### 2.1 좌표계(CRS) 통합

| 단계 | EPSG | 비고 |
|------|------|------|
| 원본 입력 | 5174 또는 5179 | 데이터셋별로 다름 — 메타 확인 후 자동 분기 |
| 내부 처리(면적·공간조인) | **5179 (UTM-K)** | 면적은 m² 단위로 계산 |
| 최종 산출물(GeoJSON/PMTiles) | **4326 (WGS84)** | MapLibre 표출용 |

`scripts/utils/crs.py` 의 `to_internal(gdf)` / `to_export(gdf)` 함수를 통해서만 변환한다.

### 2.2 공간 단위 통합 — 핵심 조인 키

| 항목 | 키 | 자릿수/타입 |
|------|-----|------------|
| 필지 식별자 | `PNU` | **문자열 19자리** (시군구5 + 읍면동3 + 리00 + 산여부1 + 본번4 + 부번4) — 앞자리 0 보존 필수 |
| 건축물 식별자(대장) | `MGM_BLDRGST_PK` | 문자열 25자리 |
| 건축물 식별자(공간) | `BD_MGT_SN` | 문자열 25자리 |
| 집계구 식별자 | `TOT_REG_CD` | 문자열 10자리 |

> ⚠️ **모든 코드 컬럼은 `dtype=str` 로 강제 로드**해야 한다. pandas 기본 추론은 PNU 앞 0을 누락시킨다.
> 예: `pd.read_csv(..., dtype={'PNU': str, 'TOT_REG_CD': str})`

### 2.3 건축물 ↔ 필지 결합 전략 (1:N 해소)

건축물대장 1건물이 여러 필지에 걸치는 경우가 있어 단순 1:1 조인은 불가하다. 다음 폴백 체계로 구현한다.

```
1순위: 건축물대장 부속지번(#9) — MGM_BLDRGST_PK ↔ PNU (모든 필지 행 펼침)
2순위: GIS건물통합정보(#7) — BD_MGT_SN ↔ MGM_BLDRGST_PK 매칭, 그 안의 PNU 사용
3순위: 공간조인 — 건물 폴리곤 centroid가 속하는 필지의 PNU
```

→ 결과 테이블 `parcel_building.parquet`:
`PNU | MGM_BLDRGST_PK | MAIN_PURPS_CD_NM | BULD_NM | match_method(1|2|3) | PLAT_AR | TOTAREA`

### 2.4 필지 단위 대표값 산정 (1필지에 여러 건물 있을 때)

1필지에 건물 N동이 있으면 **연면적(`TOTAREA`) 최대인 건물의 주용도**를 그 필지의 대표 주용도로 한다(강의 §건축물 비율 산정 관행).
동률이면 건축연도 최신, 그것도 같으면 `MGM_BLDRGST_PK` 사전순 최소.

### 2.5 용도지역 정규화

토지특성정보의 `용도지역명`은 표기 흔들림이 있다(`제1종일반주거지역` vs `1종일반주거`). 다음 규칙으로 정규화한다.

```
"제1종전용주거지역" / "1종전용" → "1종전용주거"
"제2종전용주거지역" / "2종전용" → "2종전용주거"
"제1종일반주거지역" / "1종일반" → "1종일반주거"
"제2종일반주거지역" / "2종일반" → "2종일반주거"
"제3종일반주거지역" / "3종일반" → "3종일반주거"
"준주거지역"                   → "준주거"
"중심상업지역"                 → "중심상업"
"일반상업지역"                 → "일반상업"
"근린상업지역"                 → "근린상업"
"유통상업지역"                 → "유통상업"
"전용공업지역"                 → "전용공업"
"일반공업지역"                 → "일반공업"
"준공업지역"                   → "준공업"
"보전녹지지역"                 → "보전녹지"
"생산녹지지역"                 → "생산녹지"
"자연녹지지역"                 → "자연녹지"
그 외 / null                  → "기타"
```

규칙은 `scripts/utils/normalize.py` 의 `ZONE_MAP` dict로 구현한다.

### 2.6 건축물 주용도 카테고리 묶음 (도넛차트용)

표제부의 `MAIN_PURPS_CD_NM`은 30종 이상으로 세분화돼 있다. 도넛차트의 가독성을 위해 **상위 12개 + 기타** 로 묶는다. 송파구 기준 빈도가 높은 다음 12개를 고정 카테고리로 한다:

```
공동주택, 단독주택, 제1종근린생활시설, 제2종근린생활시설,
업무시설, 교육연구시설, 판매시설, 노유자시설,
숙박시설, 문화및집회시설, 자동차관련시설, 공장
그 외 → "기타"
```

색상 팔레트(WCAG AA 대비 ≥4.5) 는 `frontend/src/constants/palette.ts` 에 고정:

```ts
export const PURPOSE_COLORS: Record<string, string> = {
  "공동주택": "#F39C12",
  "단독주택": "#3498DB",
  "제1종근린생활시설": "#F1C40F",
  "제2종근린생활시설": "#E67E22",
  "업무시설": "#2980B9",
  "교육연구시설": "#1ABC9C",
  "판매시설": "#16A085",
  "노유자시설": "#9B59B6",
  "숙박시설": "#E91E63",
  "문화및집회시설": "#8E44AD",
  "자동차관련시설": "#34495E",
  "공장": "#7F8C8D",
  "기타": "#BDC3C7",
};
```

### 2.7 송파구 공간 필터

모든 입력 데이터는 다음 한 줄로 송파구로 1차 필터한다.

```python
SONGPA_SGG_CD = "11710"   # 서울 송파구
gdf = gdf[gdf["PNU"].str[:5] == SONGPA_SGG_CD]
```

집계구는 `TOT_REG_CD` 앞 5자리, 행정구역 SHP는 `SIG_CD == "11710"` 로 필터.

---

## 3. 기술 스택 (고정)

### 3.1 전처리 파이프라인
- Python 3.11
- GeoPandas 0.14+, Shapely 2.x, pyproj 3.6+
- pandas 2.x, pyarrow (Parquet I/O)
- **tippecanoe** + **pmtiles** CLI (벡터 타일 생성)
- `lxml` (건축물대장 XML 파싱)

### 3.2 프런트엔드
- React 18 + TypeScript + Vite 5
- MapLibre GL JS 4.x (+ `pmtiles` protocol plugin)
- Tailwind CSS 3.x
- Recharts 2.x (도넛/파이 차트)
- Zustand (전역 상태)

### 3.3 베이스맵
- Vworld WMTS — `https://api.vworld.kr/req/wmts/1.0.0/{key}/Base/{z}/{y}/{x}.png`
- API key는 `.env.local` 의 `VITE_VWORLD_KEY` 로 주입

---

## 4. 디렉터리 구조 (이대로 생성할 것)

```
songpa-landuse/
├─ README.md                       ← 이 문서
├─ .env.example
├─ data/
│  ├─ raw/                         ← 원본 SHP/XML/CSV (gitignore)
│  │  ├─ admin/                    # 행정구역
│  │  ├─ parcel/                   # 연속지적도
│  │  ├─ land_char/                # 토지특성정보
│  │  ├─ building_gis/             # GIS건물통합정보
│  │  ├─ bldrgst_title/            # 건축물대장 표제부
│  │  ├─ bldrgst_jibun/            # 건축물대장 부속지번
│  │  └─ sgis/                     # 집계구 경계 + 통계
│  ├─ interim/                     ← parquet 중간 산출물
│  └─ processed/                   ← 최종 GeoJSON/PMTiles
│     ├─ admin_emd.geojson
│     ├─ oa_stats.geojson
│     ├─ parcels.pmtiles
│     └─ buildings.pmtiles
├─ scripts/
│  ├─ 00_check_env.py              # 의존성·tippecanoe 설치 확인
│  ├─ 01_load_admin.py             # 행정동 경계 → admin_emd.geojson
│  ├─ 02_load_parcels.py           # 연속지적도 + 토지특성 조인
│  ├─ 03_load_buildings.py         # GIS건물통합 + 표제부 + 부속지번 조인
│  ├─ 04_load_oa.py                # 집계구 경계 + 인구/가구
│  ├─ 05_build_parcel_attrs.py     # 필지별 대표 주용도/용도지역 산정
│  ├─ 06_generate_stats.py         # 통계표(JSON) 산출
│  ├─ 07_emit_tiles.py             # PMTiles 생성 (tippecanoe)
│  ├─ run_all.sh                   # 01→07 일괄 실행
│  └─ utils/
│     ├─ crs.py
│     ├─ normalize.py
│     ├─ io.py
│     └─ join.py
├─ frontend/
│  ├─ index.html
│  ├─ vite.config.ts
│  ├─ tailwind.config.js
│  ├─ tsconfig.json
│  ├─ package.json
│  ├─ public/
│  │  └─ data/                     ← scripts/processed/* 심볼릭 링크 또는 복사본
│  └─ src/
│     ├─ main.tsx
│     ├─ App.tsx
│     ├─ map/
│     │  ├─ MapView.tsx            # MapLibre + PMTiles 초기화
│     │  ├─ layers/
│     │  │  ├─ AdminLayer.ts
│     │  │  ├─ OALayer.ts
│     │  │  ├─ ParcelLayer.ts
│     │  │  └─ BuildingLayer.ts
│     │  └─ styles/                # mapbox-gl-style spec JSON
│     ├─ panels/
│     │  ├─ LeftSidebar.tsx        # 레이어 토글, 범례
│     │  ├─ RightStatsPanel.tsx    # 4탭 통계 + 도넛
│     │  └─ ParcelInfoCard.tsx     # 필지 클릭 정보
│     ├─ store/
│     │  └─ useAppStore.ts
│     └─ constants/
│        ├─ palette.ts
│        └─ purposeCategories.ts
└─ docs/
   └─ data_sources.md
```

---

## 5. 전처리 스크립트 명세 (입력·출력·핵심 로직)

### 5.1 `01_load_admin.py`
- 입력: `data/raw/admin/BND_ADM_DONG_PG.shp` (전국 행정동)
- 처리: `SIG_CD == "11710"` 필터 → EPSG:5179 → 유효성 검사(buffer(0)) → 4326 변환
- 출력: `data/processed/admin_emd.geojson` (27 features, 속성: `EMD_CD`, `EMD_KOR_NM`)

### 5.2 `02_load_parcels.py`
- 입력:
  - `data/raw/parcel/LSMD_CONT_LDREG_*.shp` (연속지적도)
  - `data/raw/land_char/AL_*.txt` 또는 SHP (토지특성정보)
- 처리:
  1. 두 데이터 모두 송파구 필터(`PNU.str[:5]=="11710"`)
  2. `PNU`(str) 키로 left join (필지 폴리곤 + 토지특성 속성)
  3. 용도지역 정규화(`ZONE_MAP` 적용)
  4. EPSG:5179에서 `area_m2` 컬럼 계산
- 출력: `data/interim/parcels.parquet` — `PNU, JIBUN, zone_norm, area_m2, geometry`

### 5.3 `03_load_buildings.py`
- 입력:
  - `data/raw/building_gis/TL_SPBD_BULD.shp` (GIS건물통합)
  - `data/raw/bldrgst_title/mart_djy_03.txt|xml` (표제부)
  - `data/raw/bldrgst_jibun/mart_djy_06.txt|xml` (부속지번)
- 처리:
  1. 표제부 송파구 필터: `SIGUNGU_CD == "11710"`
  2. 부속지번 송파구 필터 동일
  3. 부속지번을 펼쳐 `MGM_BLDRGST_PK ↔ PNU` 매핑 테이블 작성
  4. 표제부의 주용도(`MAIN_PURPS_CD_NM`)·연면적(`TOTAREA`) 결합
  5. GIS건물통합과 `MGM_BLDRGST_PK` 매칭 시도 → 실패한 건물은 §2.3 3순위 공간조인
- 출력:
  - `data/interim/buildings.parquet` (geometry 포함)
  - `data/interim/parcel_building.parquet` (geometry 없음, PNU↔건물 N:N)

### 5.4 `04_load_oa.py`
- 입력:
  - `data/raw/sgis/songpa_oa.shp`
  - `data/raw/sgis/oa_population_household.csv` (컬럼: `TOT_REG_CD, TOT_PPLTN, TOT_HSHLD`)
- 처리: `TOT_REG_CD`(str 10) 조인 → 4326 변환
- 출력: `data/processed/oa_stats.geojson` (속성: `TOT_REG_CD, TOT_PPLTN, TOT_HSHLD`)

### 5.5 `05_build_parcel_attrs.py`
- 입력: `parcels.parquet`, `parcel_building.parquet`
- 처리: §2.4 규칙으로 필지별 대표 주용도 산정 → 필지 테이블에 `main_purpose` 컬럼 추가
- 출력: `data/interim/parcels_final.parquet` — `PNU, JIBUN, zone_norm, main_purpose, area_m2, geometry`

### 5.6 `06_generate_stats.py`
- 입력: `parcels_final.parquet`
- 처리: 다음 4종 집계 산출
  - 주용도별: 필지 수, 면적합(m²), 구성비(%)
  - 용도지역별: 동일
  - 행정동별 × 주용도 교차표
  - 집계구별 인구/가구 요약
- 출력: `frontend/public/data/stats.json` (구조는 §7 참고)

### 5.7 `07_emit_tiles.py`
- 처리:
  ```bash
  tippecanoe -o data/processed/parcels.pmtiles \
    --layer=parcels --minimum-zoom=11 --maximum-zoom=16 \
    --drop-densest-as-needed --no-feature-limit --no-tile-size-limit \
    data/processed/parcels.geojson

  tippecanoe -o data/processed/buildings.pmtiles \
    --layer=buildings --minimum-zoom=13 --maximum-zoom=17 \
    data/processed/buildings.geojson
  ```
- 산출물을 `frontend/public/data/` 로 복사한다.

---

## 6. 프런트엔드 명세

### 6.1 지도 초기화
- 중심: `[127.1058, 37.5145]` (송파구청 부근), zoom 12
- 베이스맵: Vworld WMTS raster source
- PMTiles 프로토콜 등록: `import { Protocol } from "pmtiles"; maplibregl.addProtocol("pmtiles", new Protocol().tile);`

### 6.2 레이어 정의(아래에서 위 순서)

| 레이어 ID | 소스 | 스타일 |
|----------|------|--------|
| `vworld-base` | WMTS raster | 항상 표시 |
| `oa-fill` | `oa_stats.geojson` | 토글 켜졌을 때만 — `TOT_PPLTN` 기반 연속 컬러램프(흰→남색, 5분위) |
| `parcel-fill` | PMTiles `parcels` | `main_purpose` 별 `PURPOSE_COLORS` (선택 시) / `zone_norm` 별 (전환 토글) |
| `parcel-line` | 동일 | 1px `#999` |
| `building-fill` | PMTiles `buildings` | `main_purpose` 별 색, opacity 0.85 |
| `emd-line` | `admin_emd.geojson` | 2px `#E74C3C` 점선 |
| `emd-label` | 동일 centroid | `EMD_KOR_NM` 14px |

### 6.3 상호작용
- **필지 클릭** → `ParcelInfoCard` 에 PNU, 주소(`JIBUN`), 용도지역, 주용도, 대지면적 표시
- **집계구 호버** → 툴팁에 행정동명·총인구·가구수
- 레이어 토글 5종(좌측 사이드바)

### 6.4 통계 패널(우측, 너비 360px)
탭 4개: `건축물 주용도` / `용도지역` / `지적` / `집계구 통계`

각 탭은:
1. 도넛차트(Recharts `<PieChart>` + `innerRadius=60`)
2. 표(`<table>`, `구분 | 필지수 | 면적(m²) | 구성비(%)`)

데이터 소스: `/data/stats.json` (§5.6 산출)

---

## 7. `stats.json` 스키마

```json
{
  "summary": {
    "parcel_count": 31153,
    "building_count": 27200,
    "total_area_m2": 40524101.0,
    "emd_count": 27
  },
  "by_purpose": [
    { "key": "공동주택", "parcels": 8686, "area_m2": 24302784, "pct": 60.0 },
    { "key": "업무시설", "parcels": 454,  "area_m2": 4338849,  "pct": 10.7 }
  ],
  "by_zone": [
    { "key": "3종일반주거", "parcels": 14210, "area_m2": 18901200, "pct": 46.6 }
  ],
  "by_emd_purpose": [
    { "emd": "잠실3동", "purpose": "공동주택", "parcels": 412, "area_m2": 1234567 }
  ],
  "oa_totals": {
    "population": 668800,
    "households": 281000
  }
}
```

---

## 8. 환경 변수(.env.example)

```
VITE_VWORLD_KEY=발급받은_Vworld_API_KEY
VITE_BASEMAP_URL=https://api.vworld.kr/req/wmts/1.0.0/{key}/Base/{z}/{y}/{x}.png
```

---

## 9. 실행 절차 (에이전트가 따라야 할 순서)

```bash
# 1. 의존성 설치
python -m pip install geopandas shapely pyproj pandas pyarrow lxml
# tippecanoe: macOS는 brew install tippecanoe, Ubuntu는 apt build 또는 docker

# 2. 원본 데이터 배치 (사용자가 수동)
#    data/raw/ 하위 7개 폴더에 SHP/XML/CSV 채워둘 것

# 3. 전처리 일괄 실행
bash scripts/run_all.sh

# 4. 프런트엔드 기동
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

`run_all.sh` 는 01부터 07까지 순차 실행하고, 어느 단계 실패 시 즉시 `set -e` 로 중단한다.

---

## 10. 품질·검증 체크리스트 (구현 완료 판정 기준)

- [ ] 송파구 필지 수가 31,000~32,000 범위 (강의자료 31,153 기준)
- [ ] PNU 19자리 전부 보존(앞 0 누락 0건)
- [ ] 필지-건축물 매칭률 95% 이상 (`match_method` 별 분포 로깅)
- [ ] 행정동 27개 모두 폴리곤 유효 (`is_valid == True`)
- [ ] 집계구 면적합과 송파구 행정구역 면적의 차이 5% 이내
- [ ] 도넛차트 합계가 100.0 ± 0.1
- [ ] PMTiles 용량: parcels.pmtiles ≤ 30MB, buildings.pmtiles ≤ 40MB
- [ ] 초기 로드 후 첫 페인트 3초 이내(M2 MacBook, 100Mbps)

---

## 11. 사용자 응답 사항(요약)

- **꼭 필요한 데이터 7종**: 행정구역, 연속지적도, 토지특성정보, GIS건물통합정보, 건축물대장 표제부, 건축물대장 부속지번, **SGIS 집계구(추가 수집)**
- **사용하지 않을 데이터**: 위 표 §1.2에 명시한 28종
- **추가로 발급/다운로드해야 할 것**:
  1. SGIS 집계구 경계 SHP + 인구/가구 CSV (https://sgis.kostat.go.kr)
  2. Vworld API Key (WMTS 베이스맵용)
- **단위 통합 핵심**:
  - 좌표계: 내부 EPSG:5179 / 표출 EPSG:4326
  - 조인 키: PNU(19, str) — 모든 단계에서 dtype=str 강제
  - 1건물-N필지: 건축물대장 부속지번으로 펼침, 실패 시 BD_MGT_SN, 그래도 실패 시 공간조인
  - 1필지-N건물: 연면적 최대 건물의 주용도를 필지 대표값으로

---

문서 끝.
