import { createContext, useContext } from 'react';

export const ToastContext = createContext(null);

/**
 * const toast = useToast();
 * toast.success('Created Example Co.') · toast.error(text) · toast.info(text) · toast.show(text, {tone, duration})
 * Each returns an id for toast.dismiss(id). Use toasts for create / delete / generate; saves stay quiet.
 */
export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast() needs <ToastProvider> above it.');
  return context;
}
