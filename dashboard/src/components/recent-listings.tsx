import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import type { Listing } from "@/lib/types";
import {
  formatPrice,
  formatRelativeDate,
  listingTypeLabel,
  furnishingLabel,
} from "@/lib/utils";

export function RecentListings({ listings }: { listings: Listing[] }) {
  if (listings.length === 0) {
    return (
      <p className="text-muted-foreground text-sm py-8 text-center">
        No listings yet. The scraper will populate data once connected.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Listing</TableHead>
          <TableHead>Price</TableHead>
          <TableHead>Area</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Furnishing</TableHead>
          <TableHead>Seen</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {listings.map((listing) => (
          <TableRow key={listing.listing_id}>
            <TableCell>
              <Link
                href={`/listings/${listing.listing_id}`}
                className="font-medium hover:underline"
              >
                {listing.detailed_title ||
                  `${listing.street || "Unknown"}, ${listing.city || ""}`}
              </Link>
            </TableCell>
            <TableCell>{formatPrice(listing.total_rental_price)}/mo</TableCell>
            <TableCell>
              {listing.surface_area ? `${listing.surface_area} m²` : "N/A"}
            </TableCell>
            <TableCell>{listingTypeLabel(listing.listing_type)}</TableCell>
            <TableCell>{furnishingLabel(listing.furnishing_id)}</TableCell>
            <TableCell className="text-muted-foreground text-sm">
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
        ))}
      </TableBody>
    </Table>
  );
}
