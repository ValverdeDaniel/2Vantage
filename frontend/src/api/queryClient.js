import { QueryClient } from '@tanstack/react-query';
import { errorStatus } from '../lib/errors';

// A 4xx will not change on retry; network errors and 5xx get two more tries.
function retry(failureCount, error) {
  const status = errorStatus(error);
  if (status && status < 500) return false;
  return failureCount < 2;
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry },
    mutations: { retry: false },
  },
});
