import { QueryClient } from "@tanstack/react-query";

/* TanStack QueryClient with EOD-aligned cache settings — docs/06 §4.
   EOD data changes once per trading day so we use a long staleTime. */
export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        /* 8 hours — EOD data shouldn't need refetching within a session */
        staleTime: 8 * 60 * 60 * 1000,
        /* Keep unused data for 12 hours */
        gcTime: 12 * 60 * 60 * 1000,
        retry: 2,
        refetchOnWindowFocus: false,
      },
    },
  });
}

/* Singleton for client-side — avoids creating a new QueryClient on every render */
let clientQueryClient: QueryClient | undefined;

export function getQueryClient(): QueryClient {
  if (typeof window === "undefined") {
    return makeQueryClient();
  }
  if (!clientQueryClient) {
    clientQueryClient = makeQueryClient();
  }
  return clientQueryClient;
}
