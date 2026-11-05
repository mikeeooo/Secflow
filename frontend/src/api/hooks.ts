import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type { ReviewRequest, SimulationRequest, StreamStatus } from "./types";

export const keys = {
  overview: ["overview"] as const,
  stream: ["stream"] as const,
  transactions: (params: Record<string, string | number | undefined>) => ["transactions", params] as const,
  accounts: (params: Record<string, string | number | undefined>) => ["accounts", params] as const,
  account: (id: string) => ["account", id] as const,
  investigation: (id: string) => ["investigation", id] as const,
  options: (sender?: string) => ["simulator-options", sender ?? ""] as const,
};

export const useOverview = () => useQuery({ queryKey: keys.overview, queryFn: api.overview, refetchInterval: 10_000 });
export const useHealth = () => useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 15_000 });
export const useStreamStatus = () => useQuery({ queryKey: keys.stream, queryFn: api.streamStatus, refetchInterval: 4_000 });

export const useTransactions = (params: Record<string, string | number | undefined>) =>
  useQuery({ queryKey: keys.transactions(params), queryFn: () => api.transactions(params), placeholderData: keepPreviousData });

export const useAccounts = (params: Record<string, string | number | undefined>) =>
  useQuery({ queryKey: keys.accounts(params), queryFn: () => api.accounts(params), placeholderData: keepPreviousData });

export const useAccount = (id: string) => useQuery({ queryKey: keys.account(id), queryFn: () => api.account(id) });
export const useInvestigation = (id: string) => useQuery({ queryKey: keys.investigation(id), queryFn: () => api.investigation(id) });
export const useAlgorithms = () => useQuery({ queryKey: ["algorithms"], queryFn: api.algorithms });
export const useEvaluation = () => useQuery({ queryKey: ["evaluation"], queryFn: api.evaluation, retry: false });

export const useSimulatorOptions = (sender?: string) =>
  useQuery({ queryKey: keys.options(sender), queryFn: () => api.simulatorOptions(sender), staleTime: 5_000 });

export function useSimulate() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: SimulationRequest) => api.simulate(body),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: keys.overview });
      void client.invalidateQueries({ queryKey: ["transactions"] });
    },
  });
}

export function useReview(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: ReviewRequest) => api.review(id, body),
    onSuccess: (data) => {
      client.setQueryData(keys.investigation(id), data);
      void client.invalidateQueries({ queryKey: keys.overview });
      void client.invalidateQueries({ queryKey: ["transactions"] });
    },
  });
}

/** Stream controls are independent of the feed: they keep working when feed polling fails. */
export function useStreamControl() {
  const client = useQueryClient();
  const onSuccess = (status: StreamStatus) => client.setQueryData(keys.stream, status);
  return {
    start: useMutation({ mutationFn: api.streamStart, onSuccess }),
    stop: useMutation({ mutationFn: api.streamStop, onSuccess, retry: 2 }),
    mode: useMutation({ mutationFn: api.streamMode, onSuccess }),
  };
}
