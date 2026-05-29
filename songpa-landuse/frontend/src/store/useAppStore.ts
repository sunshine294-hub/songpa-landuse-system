import { create } from 'zustand';

export interface ParcelInfo {
  PNU: string;
  JIBUN: string;
  zone_norm: string;
  main_purpose: string;
  area_m2: number;
}

interface AppState {
  layers: {
    emdBorder: boolean;
    emdLabel: boolean;
    oaStats: boolean;
    parcel: boolean;
    building: boolean;
  };
  colorMode: 'purpose' | 'zone';
  selectedParcel: ParcelInfo | null;
  activeTab: number;
  toggleLayer: (key: keyof AppState['layers']) => void;
  setColorMode: (mode: 'purpose' | 'zone') => void;
  setSelectedParcel: (p: ParcelInfo | null) => void;
  setActiveTab: (tab: number) => void;
}

export const useAppStore = create<AppState>((set) => ({
  layers: {
    emdBorder: true,
    emdLabel: true,
    oaStats: false,
    parcel: true,
    building: false,
  },
  colorMode: 'purpose',
  selectedParcel: null,
  activeTab: 0,
  toggleLayer: (key) =>
    set((s) => ({ layers: { ...s.layers, [key]: !s.layers[key] } })),
  setColorMode: (mode) => set({ colorMode: mode }),
  setSelectedParcel: (p) => set({ selectedParcel: p }),
  setActiveTab: (tab) => set({ activeTab: tab }),
}));
