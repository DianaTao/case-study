import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ChatMessage, ApplianceType, Cart } from './types';
import { generateSessionId } from './utils';

interface ChatState {
  sessionId: string;
  messages: ChatMessage[];
  applianceType?: ApplianceType;
  modelNumber?: string;
  cartId: string;
  cart: Cart | null;
  isLoading: boolean;
  
  // Actions
  setApplianceType: (type: ApplianceType) => void;
  setModelNumber: (model: string) => void;
  addMessage: (message: ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
  setCart: (cart: Cart) => void;
  setLoading: (loading: boolean) => void;
  resetSession: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      sessionId: generateSessionId(),
      messages: [],
      applianceType: undefined,
      modelNumber: undefined,
      cartId: crypto.randomUUID(), // Use proper UUID format
      cart: null,
      isLoading: false,

      setApplianceType: (type) => set({ applianceType: type }),
      
      setModelNumber: (model) => set({ modelNumber: model }),
      
      addMessage: (message) =>
        set((state) => ({ messages: [...state.messages, message] })),
      
      setMessages: (messages) => set({ messages }),
      
      setCart: (cart) => set({ cart }),
      
      setLoading: (loading) => set({ isLoading: loading }),
      
      resetSession: () =>
        set({
          sessionId: generateSessionId(),
          messages: [],
          applianceType: undefined,
          modelNumber: undefined,
          cartId: crypto.randomUUID(), // Use proper UUID format
          cart: null,
          isLoading: false,
        }),
    }),
    {
      name: 'partselect-chat',
      partialize: (state) => ({
        sessionId: state.sessionId,
        applianceType: state.applianceType,
        modelNumber: state.modelNumber,
        cartId: state.cartId,
        messages: state.messages.slice(-10), // Keep last 10 messages
      }),
    }
  )
);
