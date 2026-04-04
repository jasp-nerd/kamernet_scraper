import { getDb } from "./db";
import type {
  Listing,
  Stats,
  PriceTrend,
  PriceDistribution,
  TypeBreakdown,
  ListingsFilter,
} from "./types";

export async function getStats(): Promise<Stats> {
  const sql = getDb();

  const [totals] = await sql`
    SELECT
      COUNT(*)::int as total_listings,
      COUNT(*) FILTER (WHERE disappeared_at IS NULL)::int as active_listings,
      COALESCE(AVG(total_rental_price) FILTER (WHERE disappeared_at IS NULL AND total_rental_price > 0), 0)::int as avg_price,
      COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_rental_price) FILTER (WHERE disappeared_at IS NULL AND total_rental_price > 0), 0)::int as median_price,
      COALESCE(AVG(surface_area) FILTER (WHERE disappeared_at IS NULL AND surface_area > 0), 0)::int as avg_area,
      COUNT(*) FILTER (WHERE first_seen_at >= CURRENT_DATE)::int as new_today,
      AVG(EXTRACT(EPOCH FROM (disappeared_at - first_seen_at)) / 86400) FILTER (WHERE disappeared_at IS NOT NULL) as avg_time_on_market_days
    FROM listings
  `;

  const byType = await sql`
    SELECT listing_type, COUNT(*)::int as count
    FROM listings WHERE disappeared_at IS NULL
    GROUP BY listing_type ORDER BY count DESC
  `;

  const byFurnishing = await sql`
    SELECT furnishing_id, COUNT(*)::int as count
    FROM listings WHERE disappeared_at IS NULL
    GROUP BY furnishing_id ORDER BY count DESC
  `;

  return {
    total_listings: totals.total_listings,
    active_listings: totals.active_listings,
    avg_price: totals.avg_price,
    median_price: totals.median_price,
    avg_area: totals.avg_area,
    new_today: totals.new_today,
    avg_time_on_market_days: totals.avg_time_on_market_days
      ? parseFloat(Number(totals.avg_time_on_market_days).toFixed(1))
      : null,
    listings_by_type: byType as unknown as Stats["listings_by_type"],
    listings_by_furnishing:
      byFurnishing as unknown as Stats["listings_by_furnishing"],
  };
}

export async function getListings(
  filters: ListingsFilter = {}
): Promise<{ listings: Listing[]; total: number }> {
  const sql = getDb();
  const {
    page = 1,
    limit = 20,
    minPrice,
    maxPrice,
    type,
    furnishing,
    minArea,
    maxArea,
    sort = "first_seen_at",
    order = "desc",
    active,
  } = filters;
  const offset = (page - 1) * limit;

  // Build WHERE conditions
  const conditions: string[] = [];
  const params: (string | number | boolean)[] = [];
  let paramIdx = 1;

  if (active !== undefined) {
    if (active) {
      conditions.push("disappeared_at IS NULL");
    } else {
      conditions.push("disappeared_at IS NOT NULL");
    }
  }
  if (minPrice !== undefined) {
    conditions.push(`total_rental_price >= $${paramIdx++}`);
    params.push(minPrice);
  }
  if (maxPrice !== undefined) {
    conditions.push(`total_rental_price <= $${paramIdx++}`);
    params.push(maxPrice);
  }
  if (type !== undefined) {
    conditions.push(`listing_type = $${paramIdx++}`);
    params.push(type);
  }
  if (furnishing !== undefined) {
    conditions.push(`furnishing_id = $${paramIdx++}`);
    params.push(furnishing);
  }
  if (minArea !== undefined) {
    conditions.push(`surface_area >= $${paramIdx++}`);
    params.push(minArea);
  }
  if (maxArea !== undefined) {
    conditions.push(`surface_area <= $${paramIdx++}`);
    params.push(maxArea);
  }

  const whereClause =
    conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";

  // Whitelist sort columns
  const allowedSorts = [
    "first_seen_at",
    "total_rental_price",
    "surface_area",
    "listing_type",
  ];
  const sortCol = allowedSorts.includes(sort) ? sort : "first_seen_at";
  const sortOrder = order === "asc" ? "ASC" : "DESC";

  const countQuery = `SELECT COUNT(*)::int as total FROM listings ${whereClause}`;
  const limitParam = paramIdx++;
  const offsetParam = paramIdx++;
  const listQuery = `SELECT * FROM listings ${whereClause} ORDER BY ${sortCol} ${sortOrder} LIMIT $${limitParam} OFFSET $${offsetParam}`;

  const [countResult] = await sql.query(countQuery, params);
  const listings = await sql.query(listQuery, [...params, limit, offset]);

  return {
    listings: listings as unknown as Listing[],
    total: countResult.total,
  };
}

export async function getListingById(id: number): Promise<Listing | null> {
  const sql = getDb();
  const rows = await sql`
    SELECT * FROM listings WHERE listing_id = ${id}
  `;
  return (rows[0] as unknown as Listing) ?? null;
}

export async function getRecentListings(limit: number = 10): Promise<Listing[]> {
  const sql = getDb();
  const rows = await sql`
    SELECT * FROM listings
    ORDER BY first_seen_at DESC
    LIMIT ${limit}
  `;
  return rows as unknown as Listing[];
}

export async function getPriceTrends(
  days: number = 30
): Promise<PriceTrend[]> {
  const sql = getDb();
  const rows = await sql`
    SELECT
      DATE(first_seen_at) as date,
      AVG(total_rental_price)::int as avg_price,
      COUNT(*)::int as count
    FROM listings
    WHERE first_seen_at >= NOW() - MAKE_INTERVAL(days => ${days})
      AND total_rental_price > 0
    GROUP BY DATE(first_seen_at)
    ORDER BY date
  `;
  return rows as unknown as PriceTrend[];
}

export async function getPriceDistribution(): Promise<PriceDistribution[]> {
  const sql = getDb();
  const rows = await sql`
    SELECT
      (FLOOR(total_rental_price / 200) * 200)::int as bucket_start,
      (FLOOR(total_rental_price / 200) * 200 + 199)::int as bucket_end,
      COUNT(*)::int as count
    FROM listings
    WHERE disappeared_at IS NULL AND total_rental_price > 0
    GROUP BY FLOOR(total_rental_price / 200)
    ORDER BY bucket_start
  `;
  return rows as unknown as PriceDistribution[];
}

export async function getTypeBreakdown(): Promise<TypeBreakdown[]> {
  const sql = getDb();
  const rows = await sql`
    SELECT
      listing_type,
      COUNT(*)::int as count,
      AVG(total_rental_price)::int as avg_price
    FROM listings
    WHERE disappeared_at IS NULL AND total_rental_price > 0
    GROUP BY listing_type
    ORDER BY count DESC
  `;
  return rows as unknown as TypeBreakdown[];
}
