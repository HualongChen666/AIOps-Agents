import { create } from 'zustand';

interface Settings {
  system_name: string;
  timezone: string;
  language: string;
  data_retention: string;
}

interface SettingsState {
  settings: Settings;
  loading: boolean;
  setSettings: (settings: Partial<Settings>) => void;
  setLoading: (loading: boolean) => void;
  resetSettings: () => void;
}

const defaultSettings: Settings = {
  system_name: 'AIOps Agent',
  timezone: 'Asia/Shanghai',
  language: 'zh-CN',
  data_retention: '30d',
};

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: defaultSettings,
  loading: false,
  setSettings: (settings) =>
    set((state) => ({
      settings: { ...state.settings, ...settings },
    })),
  setLoading: (loading) => set({ loading }),
  resetSettings: () => set({ settings: defaultSettings }),
}));