import { useEffect, useRef } from 'react';
import { useCreateAction, type CreateActionType } from '../context/CreateActionContext';

/** Open the page’s create form when the header Create button is pressed. */
export function useCreateActionListener(type: CreateActionType, onTrigger: () => void) {
  const { pendingAction, consumeAction } = useCreateAction();
  const onTriggerRef = useRef(onTrigger);
  onTriggerRef.current = onTrigger;

  useEffect(() => {
    if (pendingAction === type) {
      onTriggerRef.current();
      consumeAction();
    }
  }, [pendingAction, type, consumeAction]);
}
