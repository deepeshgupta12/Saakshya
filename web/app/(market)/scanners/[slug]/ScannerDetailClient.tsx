"use client";
import * as React from "react";
import { useScanner } from "@/hooks";
import { useFilterStore } from "@/stores/filter-store";
import { ScannerHeader, ScannerResultsTable, ScannerSkeleton } from "@/components/scanner";
import { ErrorState } from "@/components/ui";

interface Props {
  slug: string;
  label: string;
  description?: string;
  validationNote?: string;
}

export function ScannerDetailClient({ slug, label, description, validationNote }: Props) {
  const filters = useFilterStore((s) => s.scannerFilters);
  const { data, isLoading, isError, refetch } = useScanner(slug, {
    limit: filters.limit,
    offset: filters.offset,
    minScore: filters.minScore,
    sector: filters.sector,
  });

  return (
    <div className="space-y-4">
      <ScannerHeader
        scanner={label}
        description={description}
        resultCount={data?.total}
        asOf={data?.asOf}
        validationNote={validationNote}
      />

      {isLoading && <ScannerSkeleton />}
      {isError && (
        <ErrorState message="Unable to load scanner results." onRetry={() => refetch()} />
      )}
      {data && (
        <ScannerResultsTable
          results={data.results}
          onRowClick={(row) => {
            // navigation handled inside via Link
          }}
        />
      )}
    </div>
  );
}
