import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useAppStore } from '../store/useAppStore';
import { PURPOSE_COLORS, ZONE_COLORS } from '../constants/palette';

const VWORLD_KEY = import.meta.env.VITE_VWORLD_KEY || '';
const BASEMAP_URL = `https://api.vworld.kr/req/wmts/1.0.0/${VWORLD_KEY}/Base/{z}/{y}/{x}.png`;
const OSM_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';

function buildPurposeMatch(colors: Record<string, string>): (string | string[])[] {
  const result: (string | string[])[] = ['match', ['get', 'main_purpose']];
  for (const [k, v] of Object.entries(colors)) { result.push(k, v); }
  result.push('#BDC3C7');
  return result;
}

function buildZoneMatch(colors: Record<string, string>): (string | string[])[] {
  const result: (string | string[])[] = ['match', ['get', 'zone_norm']];
  for (const [k, v] of Object.entries(colors)) { result.push(k, v); }
  result.push('#BDC3C7');
  return result;
}

export default function MapView() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const { layers, colorMode, setSelectedParcel } = useAppStore();

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          'vworld-base': {
            type: 'raster',
            tiles: [VWORLD_KEY ? BASEMAP_URL : OSM_URL],
            tileSize: 256,
            attribution: 'Vworld',
          },
        },
        layers: [{ id: 'vworld-base', type: 'raster', source: 'vworld-base' }],
      },
      center: [127.1058, 37.5145],
      zoom: 13,
      maxZoom: 18,
    });

    map.addControl(new maplibregl.NavigationControl(), 'bottom-right');
    mapRef.current = map;

    map.on('load', () => {
      // Add GeoJSON sources
      const sources = [
        { id: 'admin-emd', url: '/data/dong_boundary.geojson' },
        { id: 'oa-stats', url: '/data/oa_stats.geojson' },
        { id: 'parcels', url: '/data/parcels.geojson' },
        { id: 'buildings', url: '/data/buildings.geojson' },
      ];

      for (const s of sources) {
        map.addSource(s.id, { type: 'geojson', data: s.url });
      }

      // OA fill (choropleth)
      map.addLayer({
        id: 'oa-fill', type: 'fill', source: 'oa-stats',
        paint: {
          'fill-color': [
            'interpolate', ['linear'], ['to-number', ['get', 'population'], 0],
            0, '#f0f4ff', 200, '#c3d7f7', 400, '#6fa3ef', 700, '#2563eb', 1200, '#1e3a8a'
          ],
          'fill-opacity': 0.55,
        },
        layout: { visibility: 'none' },
      });
      map.addLayer({
        id: 'oa-line', type: 'line', source: 'oa-stats',
        paint: { 'line-color': '#475569', 'line-width': 0.5 },
        layout: { visibility: 'none' },
      });

      // Parcel fill
      map.addLayer({
        id: 'parcel-fill', type: 'fill', source: 'parcels',
        paint: {
          'fill-color': buildPurposeMatch(PURPOSE_COLORS) as any,
          'fill-opacity': 0.7,
        },
        minzoom: 12.5,
      });
      map.addLayer({
        id: 'parcel-line', type: 'line', source: 'parcels',
        paint: { 'line-color': '#999', 'line-width': 0.5 },
        minzoom: 14,
      });

      // Building fill
      map.addLayer({
        id: 'building-fill', type: 'fill', source: 'buildings',
        paint: {
          'fill-color': buildPurposeMatch(PURPOSE_COLORS) as any,
          'fill-opacity': 0.85,
        },
        minzoom: 15,
        layout: { visibility: 'none' },
      });

      // Admin boundary
      map.addLayer({
        id: 'emd-line', type: 'line', source: 'admin-emd',
        paint: {
          'line-color': '#E74C3C', 'line-width': 2.5,
          'line-dasharray': [4, 3],
        },
      });

      // Admin label
      map.addLayer({
        id: 'emd-label', type: 'symbol', source: 'admin-emd',
        layout: {
          'text-field': ['get', 'ADM_NM'],
          'text-size': 14,
          'text-font': ['Open Sans Bold'],
          'text-allow-overlap': false,
        },
        paint: {
          'text-color': '#c0392b',
          'text-halo-color': '#fff',
          'text-halo-width': 2,
        },
      });

      // Parcel click handler
      map.on('click', 'parcel-fill', (e) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties;
        setSelectedParcel({
          PNU: p?.PNU || '',
          JIBUN: p?.JIBUN || '',
          zone_norm: p?.zone_norm || '',
          main_purpose: p?.main_purpose || '',
          area_m2: parseFloat(p?.area_m2) || 0,
        });
      });

      // OA hover tooltip
      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });
      popupRef.current = popup;

      map.on('mousemove', 'oa-fill', (e) => {
        if (!e.features?.length) return;
        map.getCanvas().style.cursor = 'pointer';
        const p = e.features[0].properties;
        const pop = p?.population ?? 0;
        const hh = p?.households ?? 0;
        popup.setLngLat(e.lngLat).setHTML(`
          <div style="line-height:1.6">
            <strong>📍 집계구</strong><br/>
            인구: <b>${Number(pop).toLocaleString()}명</b><br/>
            가구: <b>${Number(hh).toLocaleString()}가구</b>
          </div>
        `).addTo(map);
      });
      map.on('mouseleave', 'oa-fill', () => {
        map.getCanvas().style.cursor = '';
        popup.remove();
      });

      map.on('mouseenter', 'parcel-fill', () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'parcel-fill', () => {
        map.getCanvas().style.cursor = '';
      });
    });

    return () => { map.remove(); mapRef.current = null; };
  }, []);

  // Sync layer visibility
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const vis = (v: boolean) => (v ? 'visible' : 'none') as 'visible' | 'none';

    try {
      map.setLayoutProperty('emd-line', 'visibility', vis(layers.emdBorder));
      map.setLayoutProperty('emd-label', 'visibility', vis(layers.emdLabel));
      map.setLayoutProperty('oa-fill', 'visibility', vis(layers.oaStats));
      map.setLayoutProperty('oa-line', 'visibility', vis(layers.oaStats));
      map.setLayoutProperty('parcel-fill', 'visibility', vis(layers.parcel));
      map.setLayoutProperty('parcel-line', 'visibility', vis(layers.parcel));
      map.setLayoutProperty('building-fill', 'visibility', vis(layers.building));
    } catch { /* layers not ready yet */ }
  }, [layers]);

  // Sync color mode
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    try {
      if (colorMode === 'zone') {
        map.setPaintProperty('parcel-fill', 'fill-color', buildZoneMatch(ZONE_COLORS) as any);
      } else {
        map.setPaintProperty('parcel-fill', 'fill-color', buildPurposeMatch(PURPOSE_COLORS) as any);
      }
    } catch { /* layer not ready */ }
  }, [colorMode]);

  return <div ref={mapContainer} style={{ flex: 1, height: '100%' }} />;
}
