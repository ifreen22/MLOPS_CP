import { create } from 'zustand';

interface AppState {
  targetCluster: string;
  setTargetCluster: (cluster: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  targetCluster: 'prod-us-east-k8s',
  setTargetCluster: (cluster) => set({ targetCluster: cluster }),
}));
