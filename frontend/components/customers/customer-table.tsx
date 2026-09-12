"use client";

import * as React from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { Pagination } from "@/components/data/pagination";
import { SortHeader } from "@/components/data/sort-header";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { usePagedQuery } from "@/hooks/use-paged-query";
import { listCustomers } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Customer } from "@/types";

type CustomerSort = "id" | "first_name" | "last_name" | "email" | "created_at";

const SORT_OPTIONS: { value: CustomerSort; label: string }[] = [
  { value: "first_name", label: "First name" },
  { value: "last_name", label: "Last name" },
  { value: "email", label: "Email" },
  { value: "created_at", label: "Created" },
];

function useDebounced(value: string, delayMs: number): string {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

/** Customer table: search, location filters, sorting, pagination. */
export function CustomerTable() {
  const [searchInput, setSearchInput] = React.useState("");
  const [city, setCity] = React.useState("");
  const [country, setCountry] = React.useState("");
  const [sortBy, setSortBy] = React.useState<CustomerSort>("first_name");
  const [order, setOrder] = React.useState<"asc" | "desc">("asc");
  const search = useDebounced(searchInput.trim(), 400);
  const resetKey = JSON.stringify({ search, city: city.trim(), country: country.trim(), sortBy, order });

  const load = React.useCallback(
    (page: number, signal: AbortSignal) =>
      listCustomers(
        {
          page,
          page_size: 20,
          search: search || undefined,
          city: city.trim() || undefined,
          country: country.trim() || undefined,
          sort_by: sortBy,
          order,
        },
        signal,
      ),
    [search, city, country, sortBy, order],
  );
  const query = usePagedQuery<Customer>("customers", load, resetKey);

  const toggleSort = (column: CustomerSort) => {
    if (sortBy === column) {
      setOrder((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(column);
      setOrder("asc");
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Customers"
        description="Search, filter, and inspect customer intelligence profiles."
      />
      <form
        role="search"
        aria-label="Customer filters"
        className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4"
        onSubmit={(event) => event.preventDefault()}
      >
        <div className="flex flex-col gap-1">
          <Label htmlFor="customer-search">Search</Label>
          <div className="relative">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            />
            <Input
              id="customer-search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Name or email…"
              className="pl-8"
              autoComplete="off"
            />
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="customer-city">City</Label>
          <Input
            id="customer-city"
            value={city}
            onChange={(event) => setCity(event.target.value)}
            placeholder="Exact city…"
            autoComplete="off"
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="customer-country">Country</Label>
          <Input
            id="customer-country"
            value={country}
            onChange={(event) => setCountry(event.target.value)}
            placeholder="Exact country…"
            autoComplete="off"
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="customer-sort">Sort by</Label>
          <Select
            value={sortBy}
            onValueChange={(value) => setSortBy(value as CustomerSort)}
          >
            <SelectTrigger id="customer-sort">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SORT_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label} ({order === "asc" ? "A–Z" : "Z–A"})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </form>

      {(search || city.trim() || country.trim()) && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span role="status">
            {query.loading ? "Searching…" : `${query.total} matching customer${query.total === 1 ? "" : "s"}`}
          </span>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setSearchInput("");
              setCity("");
              setCountry("");
            }}
          >
            Clear filters
          </Button>
        </div>
      )}

      {query.loading ? (
        <div className="flex flex-col gap-2" role="status" aria-label="Loading customers">
          {Array.from({ length: 8 }, (_, index) => (
            <Skeleton key={index} className="h-10" />
          ))}
        </div>
      ) : query.error !== null ? (
        <ErrorState
          title="Unable to load customers"
          description={query.error}
          onRetry={query.retry}
        />
      ) : query.items.length === 0 ? (
        <EmptyState
          title="No customers found"
          description="No customer records match the current search and filters. Adjust or clear them to see more."
          actionLabel="Clear filters"
          onAction={() => {
            setSearchInput("");
            setCity("");
            setCountry("");
          }}
        />
      ) : (
        <>
          <Table aria-label="Customers">
            <TableHeader>
              <TableRow>
                <SortHeader
                  label="Name"
                  active={sortBy === "first_name"}
                  direction={order}
                  onToggle={() => toggleSort("first_name")}
                />
                <TableHead>Email</TableHead>
                <TableHead>City</TableHead>
                <TableHead>Country</TableHead>
                <SortHeader
                  label="Created"
                  active={sortBy === "created_at"}
                  direction={order}
                  onToggle={() => toggleSort("created_at")}
                />
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.items.map((customer) => (
                <TableRow key={customer.id}>
                  <TableCell>
                    <Link
                      href={`/customers/${customer.id}`}
                      className="font-medium underline-offset-4 hover:underline"
                    >
                      {customer.first_name} {customer.last_name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{customer.email}</TableCell>
                  <TableCell>{customer.city ?? "—"}</TableCell>
                  <TableCell>{customer.country ?? "—"}</TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {formatDate(customer.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Pagination
            page={query.page}
            pageCount={query.pageCount}
            total={query.total}
            onPageChange={query.setPage}
          />
        </>
      )}
    </div>
  );
}
