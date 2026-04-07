import Link from "next/link";
import { notFound } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { getListingById } from "@/lib/queries";
import {
  formatPrice,
  formatDate,
  formatDateTime,
  formatRelativeDate,
  listingTypeLabel,
  furnishingLabel,
  energyLabel,
} from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function ListingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const listing = await getListingById(Number(id));

  if (!listing) {
    notFound();
  }

  const kamernet_url = `https://kamernet.nl/huren/${listing.city_slug ?? "amsterdam"}/${listing.street_slug ?? ""}/${listing.listing_id}`;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link
          href="/listings"
          className="inline-flex items-center justify-center rounded-lg border border-border bg-background px-2.5 h-7 text-sm font-medium hover:bg-muted"
        >
          Back
        </Link>
        <h1 className="text-2xl font-bold flex-1">
          {listing.detailed_title ||
            `${listing.street || "Unknown"}, ${listing.city || ""}`}
        </h1>
        <div className="flex gap-2">
          {listing.is_new_advert && <Badge>New</Badge>}
          {listing.is_top_advert && <Badge variant="secondary">Featured</Badge>}
          {listing.disappeared_at ? (
            <Badge variant="secondary">Gone</Badge>
          ) : (
            <Badge variant="default">Active</Badge>
          )}
        </div>
      </div>

      {/* Images */}
      {listing.full_preview_image_url && (
        <div className="rounded-lg overflow-hidden border max-w-2xl">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={listing.full_preview_image_url}
            alt={listing.detailed_title ?? "Listing image"}
            className="w-full h-auto object-cover max-h-96"
          />
        </div>
      )}

      {listing.additional_images && listing.additional_images.length > 0 && (
        <div className="flex gap-3 overflow-x-auto">
          {listing.additional_images.map((url, i) => (
            <div
              key={i}
              className="rounded-lg overflow-hidden border flex-shrink-0 w-48 h-32"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={url}
                alt={`Image ${i + 1}`}
                className="w-full h-full object-cover"
              />
            </div>
          ))}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {/* Property Details */}
        <Card>
          <CardHeader>
            <CardTitle>Property Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <DetailRow label="Price" value={`${formatPrice(listing.total_rental_price)}/mo`} />
            <DetailRow label="Deposit" value={listing.deposit ? formatPrice(listing.deposit) : "N/A"} />
            <DetailRow label="Area" value={listing.surface_area ? `${listing.surface_area} m²` : "N/A"} />
            <DetailRow label="Type" value={listingTypeLabel(listing.listing_type)} />
            <DetailRow label="Furnishing" value={furnishingLabel(listing.furnishing_id)} />
            <DetailRow label="Rooms" value={listing.num_rooms?.toString() ?? "N/A"} />
            <DetailRow label="Bedrooms" value={listing.num_bedrooms?.toString() ?? "N/A"} />
            <DetailRow label="Energy Label" value={energyLabel(listing.energy_label_id)} />
            <DetailRow
              label="Utilities"
              value={
                listing.utilities_included === true
                  ? "Included"
                  : listing.utilities_included === false
                    ? "Not included"
                    : "N/A"
              }
            />
          </CardContent>
        </Card>

        {/* Location & Availability */}
        <Card>
          <CardHeader>
            <CardTitle>Location & Availability</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <DetailRow label="Street" value={listing.street ?? "N/A"} />
            <DetailRow label="City" value={listing.city ?? "N/A"} />
            <DetailRow label="Postal Code" value={listing.postal_code ?? "N/A"} />
            <DetailRow
              label="Address"
              value={
                listing.house_number
                  ? `${listing.house_number}${listing.house_number_addition ?? ""}`
                  : "N/A"
              }
            />
            <Separator />
            <DetailRow label="Available From" value={formatDate(listing.availability_start)} />
            <DetailRow
              label="Available Until"
              value={listing.availability_end ? formatDate(listing.availability_end) : "Indefinite"}
            />
          </CardContent>
        </Card>

        {/* Tenant Preferences */}
        <Card>
          <CardHeader>
            <CardTitle>Tenant Preferences</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <DetailRow
              label="Age Range"
              value={
                listing.min_age && listing.max_age
                  ? `${listing.min_age} - ${listing.max_age}`
                  : "No restriction"
              }
            />
            <DetailRow
              label="Pets"
              value={
                listing.pets_allowed === true
                  ? "Allowed"
                  : listing.pets_allowed === false
                    ? "Not allowed"
                    : "N/A"
              }
            />
            <DetailRow
              label="Smoking"
              value={
                listing.smoking_allowed === true
                  ? "Allowed"
                  : listing.smoking_allowed === false
                    ? "Not allowed"
                    : "N/A"
              }
            />
            <DetailRow
              label="Registration"
              value={
                listing.registration_allowed === true
                  ? "Possible"
                  : listing.registration_allowed === false
                    ? "Not possible"
                    : "N/A"
              }
            />
            <DetailRow
              label="Suitable For"
              value={
                listing.suitable_for_persons
                  ? `${listing.suitable_for_persons} person(s)`
                  : "N/A"
              }
            />
          </CardContent>
        </Card>

        {/* Landlord */}
        <Card>
          <CardHeader>
            <CardTitle>Landlord</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <DetailRow
              label="Name"
              value={
                listing.landlord_name
                  ? `${listing.landlord_name}${listing.landlord_verified ? " (Verified)" : ""}`
                  : "N/A"
              }
            />
            <DetailRow
              label="Response Rate"
              value={
                listing.landlord_response_rate !== null
                  ? `${listing.landlord_response_rate}%`
                  : "N/A"
              }
            />
            <DetailRow label="Response Time" value={listing.landlord_response_time ?? "N/A"} />
            <DetailRow
              label="Active Listings"
              value={listing.landlord_active_listings?.toString() ?? "N/A"}
            />
            <DetailRow label="Member Since" value={formatDate(listing.landlord_member_since)} />
            <DetailRow label="Last Seen" value={formatRelativeDate(listing.landlord_last_seen)} />
          </CardContent>
        </Card>
      </div>

      {/* AI Score */}
      {listing.ai_score != null && (
        <Card>
          <CardHeader>
            <CardTitle>AI Score</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-4xl font-bold text-center">
              <span
                className={
                  listing.ai_score >= 70
                    ? "text-green-600"
                    : listing.ai_score >= 40
                      ? "text-yellow-600"
                      : "text-red-500"
                }
              >
                {listing.ai_score}/100
              </span>
            </div>
            {listing.ai_score_reasoning && (
              <p className="text-sm text-muted-foreground text-center">
                {listing.ai_score_reasoning}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Description */}
      {listing.detailed_description && (
        <Card>
          <CardHeader>
            <CardTitle>Description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {listing.detailed_description}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Tracking Info */}
      <Card>
        <CardHeader>
          <CardTitle>Tracking Info</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <DetailRow label="First Seen" value={formatDateTime(listing.first_seen_at)} />
          <DetailRow label="Last Seen" value={formatDateTime(listing.last_seen_at)} />
          <DetailRow
            label="Disappeared"
            value={listing.disappeared_at ? formatDateTime(listing.disappeared_at) : "Still active"}
          />
          <DetailRow label="Published" value={formatDateTime(listing.publish_date)} />
          <DetailRow label="Listing ID" value={listing.listing_id.toString()} />
          <Separator />
          <a
            href={kamernet_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:underline"
          >
            View on Kamernet.nl
          </a>
        </CardContent>
      </Card>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}
