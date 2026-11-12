import { QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import { queryClient } from './api/queryClient';
import App from './App';
import AuthProvider from './auth/AuthProvider';
// The old app's sheets, in the old order, through one manifest: the only stylesheet the app imports (plan.md §3.9,
// O.5). Every component uses their class names; there are no CSS modules and no per-route sheets.
import './styles/index.css';
import ToastProvider from './ui/Toast';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ToastProvider>
          <AuthProvider>
            <App />
          </AuthProvider>
        </ToastProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
