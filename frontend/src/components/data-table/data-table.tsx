"use client";

import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type PaginationState,
} from "@tanstack/react-table";
import { EmptyState } from "@/components/shared/empty-state";
import { DataTablePagination } from "@/components/data-table/data-table-pagination";
import { useTranslations } from "next-intl";

interface DataTableProps<TData> {
  columns: ColumnDef<TData, unknown>[];
  data: TData[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  isLoading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  onRowClick?: (row: TData) => void;
}

export function DataTable<TData>({
  columns,
  data,
  total,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  isLoading = false,
  emptyTitle,
  emptyDescription,
  onRowClick,
}: DataTableProps<TData>) {
  const t = useTranslations("common");

  const pagination: PaginationState = {
    pageIndex: page - 1,
    pageSize,
  };

  const pageCount = Math.ceil(total / pageSize);

  const table = useReactTable({
    data,
    columns,
    pageCount,
    state: { pagination },
    onPaginationChange: (updater) => {
      const next =
        typeof updater === "function" ? updater(pagination) : updater;
      onPageChange(next.pageIndex + 1);
      if (onPageSizeChange && next.pageSize !== pageSize) {
        onPageSizeChange(next.pageSize);
      }
    },
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
  });

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border/50 bg-card">
        <div className="relative overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr
                  key={headerGroup.id}
                  className="border-b border-border/50 bg-muted/30"
                >
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-4 py-3 text-left font-medium text-muted-foreground"
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-border/40">
                    {columns.map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : table.getRowModel().rows.length === 0 ? (
                <tr>
                  <td colSpan={columns.length}>
                    <EmptyState
                      title={emptyTitle ?? t("noData")}
                      description={emptyDescription}
                    />
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    className={`border-b border-border/40 last:border-b-0 transition-colors hover:bg-muted/30${
                      onRowClick ? " cursor-pointer" : ""
                    }`}
                    onClick={() => onRowClick?.(row.original)}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3">
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {!isLoading && total > 0 && (
        <DataTablePagination
          page={page}
          pageSize={pageSize}
          total={total}
          pageCount={pageCount}
          onPageChange={onPageChange}
          onPageSizeChange={onPageSizeChange}
        />
      )}
    </div>
  );
}
