import Link from "next/link";
import { Suspense } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { FilterBar } from "@/components/filter-bar";
import { getListings } from "@/lib/queries";
import type { ListingsFilter } from "@/lib/types";
import {
  formatPrice,
  formatRelativeDate,
  listingTypeLabel,
  furnishingLabel,
} from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function ListingsPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;

  const filters: ListingsFilter = {
    page: params.page ? Number(params.page) : 1,
    limit: 20,
    sort: (params.sort as string) ?? "first_seen_at",
    order: (params.order as "asc" | "desc") ?? "desc",
  };

  if (params.minPrice) filters.minPrice = Number(params.minPrice);
  if (params.maxPrice) filters.maxPrice = Number(params.maxPrice);
  if (params.type && params.type !== "all")
    filters.type = Number(params.type);
  if (params.furnishing && params.furnishing !== "all")
    filters.furnishing = Number(params.furnishing);
  if (params.minArea) filters.minArea = Number(params.minArea);
  if (params.maxArea) filters.maxArea = Number(params.maxArea);
  if (params.active === "true") filters.active = true;
  if (params.active === "false") filters.active = false;

  const { listings, total } = await getListings(filters);
  const totalPages = Math.ceil(total / (filters.limit ?? 20));
  const currentPage = filters.page ?? 1;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Listings</h1>

      <Suspense>
        <FilterBar />
      </Suspense>

      <p className="text-sm text-muted-foreground">
        {total} listing{total !== 1 ? "s" : ""} found
      </p>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="min-w-[200px]">Listing</TableHead>
              <TableHead>Price</TableHead>
              <TableHead>Area</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Furnishing</TableHead>
              <TableHead>City</TableHead>
              <TableHead>Seen</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {listings.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  No listings found
                </TableCell>
              </TableRow>
            ) : (
              listings.map((listing) => (
                <TableRow key={listing.listing_id}>
                  <TableCell>
                    <Link
                      href={`/listings/${listing.listing_id}`}
                      className="font-medium hover:underline line-clamp-1"
                    >
                      {listing.detailed_title ||
                        listing.street ||
                        `Listing #${listing.listing_id}`}
                    </Link>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {formatPrice(listing.total_rental_price)}/mo
                  </TableCell>
                  <TableCell>
                    {listing.surface_area ? `${listing.surface_area} m²` : "—"}
                  </TableCell>
                  <TableCell>{listingTypeLabel(listing.listing_type)}</TableCell>
                  <TableCell>{furnishingLabel(listing.furnishing_id)}</TableCell>
                  <TableCell>{listing.city ?? "—"}</TableCell>
                  <TableCell className="text-muted-foreground text-sm whitespace-nowrap">
                    {formatRelativeDate(listing.first_seen_at)}
                  </TableCell>
                  <TableCell>
                    {listing.disappeared_at ? (
                      <Badge variant="secondary">Gone</Badge>
                    ) : (
                      <Badge variant="default">Active</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {totalPages > 1 && (
        <div className="flex gap-2 justify-center">
          {currentPage > 1 && (
            <Link
              href={`/listings?${new URLSearchParams({
                ...Object.fromEntries(
                  Object.entries(params).filter(
                    ([, v]) => v !== undefined
                  ) as [string, string][]
                ),
                page: String(currentPage - 1),
              }).toString()}`}
              className="inline-flex items-center justify-center rounded-lg border border-border bg-background px-2.5 h-7 text-sm font-medium hover:bg-muted"
            >
              Previous
            </Link>
          )}
          <span className="flex items-center text-sm text-muted-foreground px-3">
            Page {currentPage} of {totalPages}
          </span>
          {currentPage < totalPages && (
            <Link
              href={`/listings?${new URLSearchParams({
                ...Object.fromEntries(
                  Object.entries(params).filter(
                    ([, v]) => v !== undefined
                  ) as [string, string][]
                ),
                page: String(currentPage + 1),
              }).toString()}`}
              className="inline-flex items-center justify-center rounded-lg border border-border bg-background px-2.5 h-7 text-sm font-medium hover:bg-muted"
            >
              Next
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
