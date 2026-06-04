import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

export type CreateActionType = 'enquiry' | 'vendor' | 'worker' | 'dish' | 'invoice';

type CreateActionContextValue = {
  pendingAction: CreateActionType | null;
  triggerCreate: (type: CreateActionType) => void;
  consumeAction: () => void;
};

const CreateActionContext = createContext<CreateActionContextValue | null>(null);

export function CreateActionProvider({ children }: { children: ReactNode }) {
  const [pendingAction, setPendingAction] = useState<CreateActionType | null>(null);

  const triggerCreate = useCallback((type: CreateActionType) => {
    setPendingAction(type);
  }, []);

  const consumeAction = useCallback(() => {
    setPendingAction(null);
  }, []);

  const value = useMemo(
    () => ({ pendingAction, triggerCreate, consumeAction }),
    [pendingAction, triggerCreate, consumeAction],
  );

  return (
    <CreateActionContext.Provider value={value}>{children}</CreateActionContext.Provider>
  );
}

export function useCreateAction() {
  const ctx = useContext(CreateActionContext);
  if (!ctx) throw new Error('useCreateAction must be used within CreateActionProvider');
  return ctx;
}
