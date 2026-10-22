import { create } from 'zustand';

interface GlobalState {
  activeSituationId: string | null;
  setActiveSituationId: (id: string | null) => void;
  graphEnvironment: string;
  setGraphEnvironment: (env: string) => void;
  graphFilters: {
    showTier0: boolean;
    showTier1: boolean;
    showTier2: boolean;
    anomalyThreshold: number;
  };
  setGraphFilters: (filters: Partial<GlobalState['graphFilters']>) => void;
}

export const useGlobalStore = create<GlobalState>((set) => ({
  activeSituationId: 'SIT-4471', // Default active for demo purposes
  setActiveSituationId: (id) => set({ activeSituationId: id }),
  graphEnvironment: 'prod-us-east',
  setGraphEnvironment: (env) => set({ graphEnvironment: env }),
  graphFilters: {
    showTier0: true,
    showTier1: true,
    showTier2: false,
    anomalyThreshold: 0.70
  },
  setGraphFilters: (filters) => set((state) => ({ 
    graphFilters: { ...state.graphFilters, ...filters } 
  }))
}));
