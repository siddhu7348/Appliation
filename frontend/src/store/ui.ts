import { create } from 'zustand';
import type { ConfidenceMode } from '@/types/api';

interface UiState {
  confidenceMode: ConfidenceMode;
  selectedStore: number | null;
  selectedProduct: string | null;
  sidebarOpen: boolean;
  setConfidenceMode: (mode: ConfidenceMode) => void;
  setSelectedStore: (store: number | null) => void;
  setSelectedProduct: (product: string | null) => void;
  toggleSidebar: () => void;
}

export const useUiStore = create<UiState>((set) => ({
  confidenceMode: 'balanced',
  selectedStore: null,
  selectedProduct: null,
  sidebarOpen: false,
  setConfidenceMode: (confidenceMode) => set({ confidenceMode }),
  setSelectedStore: (selectedStore) => set({ selectedStore }),
  setSelectedProduct: (selectedProduct) => set({ selectedProduct }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
}));
