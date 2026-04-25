'use client';

import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';
import { knowledgeSearch } from '@/lib/api';
import { SearchBar } from '@/components/knowledge/SearchBar';
import { FilterSidebar } from '@/components/knowledge/FilterSidebar';
import { IncidentCard } from '@/components/knowledge/IncidentCard';

export function KnowledgeSearch() {
  const searchParams = useSearchParams();
  const q = searchParams.get('q') ?? '';
  const category = searchParams.get('category') ?? undefined;
  const resolution_category = searchParams.get('resolution_category') ?? undefined;

  const { data, isLoading } = useQuery({
    queryKey: ['knowledge', 'search', q, category, resolution_category],
    queryFn: () => knowledgeSearch(q, { ...(category ? { category } : {}), ...(resolution_category ? { resolution_category } : {}) }),
    staleTime: 60_000,
  });

  return (
    <div className="space-y-4">
      <SearchBar />
      <div className="flex gap-6">
        <FilterSidebar />
        <div className="flex-1 space-y-3">
          {isLoading && <div className="text-sm text-muted-foreground animate-pulse">Searching…</div>}
          {data?.length === 0 && (
            <div className="text-sm text-muted-foreground">No results found.</div>
          )}
          {data?.map((inc) => (
            <IncidentCard key={inc.id as string} incident={inc as unknown as Record<string, unknown>} />
          ))}
        </div>
      </div>
    </div>
  );
}
