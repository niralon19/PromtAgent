import { useQuery } from '@tanstack/react-query';
import {
  getActionMetrics,
  getQualityMetrics,
  getOperationalMetrics,
  getSystemHealth,
  getRecentPatterns,
} from '@/lib/api';

export const useActionMetrics = () =>
  useQuery({ queryKey: ['metrics', 'actions'], queryFn: getActionMetrics, staleTime: 60_000 });

export const useQualityMetrics = () =>
  useQuery({ queryKey: ['metrics', 'quality'], queryFn: getQualityMetrics, staleTime: 60_000 });

export const useOperationalMetrics = () =>
  useQuery({ queryKey: ['metrics', 'operational'], queryFn: getOperationalMetrics, staleTime: 60_000 });

export const useSystemHealth = () =>
  useQuery({ queryKey: ['system', 'health'], queryFn: getSystemHealth, staleTime: 30_000, refetchInterval: 30_000 });

export const useRecentPatterns = () =>
  useQuery({ queryKey: ['patterns', 'recent'], queryFn: getRecentPatterns, staleTime: 300_000 });
