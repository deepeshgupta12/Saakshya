"use client";
import { useScannerList } from "@/hooks";
import { ScannerCard } from "@/components/scanner";
import { Skeleton, ErrorState } from "@/components/ui";

export function ScannerDirectoryClient() {
  const { data, isLoading, isError, refetch } = useScannerList();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1,2,3,4].map((i) => <Skeleton key={i} className="h-28" />)}
      </div>
    );
  }

  if (isError || !data) {
    return <ErrorState message="Unable to load scanner directory." onRetry={() => refetch()} />;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {data.map((scanner) => <ScannerCard key={scanner.scanner} scanner={scanner} />)}
    </div>
  );
}
