import { getDb } from "./db";
import type {
  Listing,
  Stats,
  PriceTrend,
  PriceDistribution,
  TypeBreakdown,
  ListingsFilter,
  CityStat,
  ScoreBucket,
  HeatmapCell,
  PriceAreaPoint,
  LandlordStat,
  EnergyStat,
  FurnishingStat,
  MarketPulse,
  TopListing,
  PricePerSqmBucket,
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
    minScore,
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
  if (minScore !== undefined) {
    conditions.push(`ai_score >= $${paramIdx++}`);
    params.push(minScore);
  }

  const whereClause =
    conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";

  // Whitelist sort columns
  const allowedSorts = [
    "first_seen_at",
    "total_rental_price",
    "surface_area",
    "listing_type",
    "ai_score",
  ];
  const sortCol = allowedSorts.includes(sort) ? sort : "first_seen_at";
  const sortOrder = order === "asc" ? "ASC" : "DESC";

  const countQuery = `SELECT COUNT(*)::int as total FROM listings ${whereClause}`;
  const limitParam = paramIdx++;
  const offsetParam = paramIdx++;
  const listQuery = `SELECT * FROM listings ${whereClause} ORDER BY ${sortCol} ${sortOrder} LIMIT $${limitParam} OFFSET $${offsetParam}`;

  const [countResult] = await sql.unsafe(countQuery, params);
  const listings = await sql.unsafe(listQuery, [...params, limit, offset]);

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
    WHERE total_rental_price > 0
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
    WHERE total_rental_price > 0
    GROUP BY listing_type
    ORDER BY count DESC
  `;
  return rows as unknown as TypeBreakdown[];
}

// ----- Extended analytics (across ALL listings, active + gone) -----

export async function getCityStats(limit: number = 10): Promise<CityStat[]> {
  const sql = getDb();
  const rows = await sql`
    SELECT
      city,
      COUNT(*)::int as count,
      COALESCE(AVG(total_rental_price) FILTER (WHERE total_rental_price > 0), 0)::int as avg_price,
      COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_rental_price) FILTER (WHERE total_rental_price > 0), 0)::int as median_price,
      COALESCE(AVG(surface_area) FILTER (WHERE surface_area > 0), 0)::int as avg_area,
      AVG(total_rental_price::numeric / NULLIF(surface_area, 0))
        FILTER (WHERE total_rental_price > 0 AND surface_area > 0) as avg_price_per_sqm
    FROM listings
    WHERE city IS NOT NULL
    GROUP BY city
    ORDER BY count DESC
    LIMIT ${limit}
  `;
  return rows.map((r: Record<string, unknown>) => ({
    city: r.city as string,
    count: r.count as number,
    avg_price: r.avg_price as number,
    median_price: r.median_price as number,
    avg_area: r.avg_area as number,
    avg_price_per_sqm:
      r.avg_price_per_sqm != null
        ? parseFloat(Number(r.avg_price_per_sqm).toFixed(1))
        : null,
  }));
}

export async function getScoreDistribution(): Promise<ScoreBucket[]> {
  const sql = getDb();
  // 5 buckets: 0-19, 20-39, 40-59, 60-79, 80-100
  const rows = await sql`
    SELECT
      CASE
        WHEN ai_score < 20 THEN '0-19'
        WHEN ai_score < 40 THEN '20-39'
        WHEN ai_score < 60 THEN '40-59'
        WHEN ai_score < 80 THEN '60-79'
        ELSE '80-100'
      END as bucket,
      CASE
        WHEN ai_score < 20 THEN 0
        WHEN ai_score < 40 THEN 20
        WHEN ai_score < 60 THEN 40
        WHEN ai_score < 80 THEN 60
        ELSE 80
      END as min_score,
      CASE
        WHEN ai_score < 20 THEN 19
        WHEN ai_score < 40 THEN 39
        WHEN ai_score < 60 THEN 59
        WHEN ai_score < 80 THEN 79
        ELSE 100
      END as max_score,
      COUNT(*)::int as count
    FROM listings
    WHERE ai_score IS NOT NULL
    GROUP BY 1, 2, 3
    ORDER BY min_score
  `;
  return rows as unknown as ScoreBucket[];
}

export async function getHourlyHeatmap(): Promise<HeatmapCell[]> {
  const sql = getDb();
  const rows = await sql`
    SELECT
      EXTRACT(DOW FROM first_seen_at)::int as dow,
      EXTRACT(HOUR FROM first_seen_at)::int as hour,
      COUNT(*)::int as count
    FROM listings
    GROUP BY dow, hour
    ORDER BY dow, hour
  `;
  return rows as unknown as HeatmapCell[];
}

export async function getPriceAreaScatter(
  limit: number = 500
): Promise<PriceAreaPoint[]> {
  const sql = getDb();
  const rows = await sql`
    SELECT
      listing_id,
      total_rental_price as price,
      surface_area as area,
      listing_type as type,
      ai_score as score,
      city,
      street
    FROM listings
    WHERE total_rental_price > 0 AND surface_area > 0
    ORDER BY first_seen_at DESC
    LIMIT ${limit}
  `;
  return rows as unknown as PriceAreaPoint[];
}

export async function getLandlordStats(limit: number = 10): Promise<LandlordStat[]> {
  const sql = getDb();
  const rows = await sql`
    SELECT
      landlord_name,
      COUNT(*)::int as count,
      BOOL_OR(landlord_verified) as verified,
      COALESCE(AVG(total_rental_price) FILTER (WHERE total_rental_price > 0), 0)::int as avg_price,
      AVG(ai_score) FILTER (WHERE ai_score IS NOT NULL) as avg_score
    FROM listings
    WHERE landlord_name IS NOT NULL
    GROUP BY landlord_name
    ORDER BY count DESC, avg_price DESC
    LIMIT ${limit}
  `;
  return rows.map((r: Record<string, unknown>) => ({
    landlord_name: r.landlord_name as string,
    count: r.count as number,
    verified: r.verified as boolean,
    avg_price: r.avg_price as number,
    avg_score:
      r.avg_score != null ? parseFloat(Number(r.avg_score).toFixed(1)) : null,
  }));
}

export async function getEnergyStats(): Promise<EnergyStat[]> {
  const sql = getDb();
  const rows = await sql`
    SELECT
      energy_label_id,
      COUNT(*)::int as count,
      COALESCE(AVG(total_rental_price) FILTER (WHERE total_rental_price > 0), 0)::int as avg_price
    FROM listings
    GROUP BY energy_label_id
    ORDER BY energy_label_id NULLS LAST
  `;
  return rows as unknown as EnergyStat[];
}

export async function getFurnishingStats(): Promise<FurnishingStat[]> {
  const sql = getDb();
  const rows = await sql`
    SELECT
      furnishing_id,
      COUNT(*)::int as count,
      COALESCE(AVG(total_rental_price) FILTER (WHERE total_rental_price > 0), 0)::int as avg_price
    FROM listings
    GROUP BY furnishing_id
    ORDER BY count DESC
  `;
  return rows as unknown as FurnishingStat[];
}

export async function getMarketPulse(): Promise<MarketPulse> {
  const sql = getDb();
  const [row] = await sql`
    SELECT
      COUNT(*)::int as total_listings,
      COUNT(*) FILTER (WHERE disappeared_at IS NULL)::int as active_listings,
      COUNT(*) FILTER (WHERE disappeared_at IS NOT NULL)::int as disappeared_listings,
      AVG(EXTRACT(EPOCH FROM (disappeared_at - first_seen_at)) / 3600)
        FILTER (WHERE disappeared_at IS NOT NULL) as avg_lifespan_hours,
      PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (disappeared_at - first_seen_at)) / 3600
      ) FILTER (WHERE disappeared_at IS NOT NULL) as median_lifespan_hours,
      COUNT(*) FILTER (WHERE first_seen_at >= NOW() - INTERVAL '24 hours')::int as new_24h,
      COUNT(*) FILTER (WHERE disappeared_at >= NOW() - INTERVAL '24 hours')::int as gone_24h
    FROM listings
  `;

  const [runs] = await sql`
    SELECT
      COUNT(*) FILTER (WHERE started_at >= NOW() - INTERVAL '24 hours')::int as scrape_runs_24h,
      MAX(started_at) as last_run_at
    FROM scrape_runs
  `;

  return {
    total_listings: row.total_listings,
    active_listings: row.active_listings,
    disappeared_listings: row.disappeared_listings,
    avg_lifespan_hours:
      row.avg_lifespan_hours != null
        ? parseFloat(Number(row.avg_lifespan_hours).toFixed(1))
        : null,
    median_lifespan_hours:
      row.median_lifespan_hours != null
        ? parseFloat(Number(row.median_lifespan_hours).toFixed(1))
        : null,
    scrape_runs_24h: runs.scrape_runs_24h,
    new_24h: row.new_24h,
    gone_24h: row.gone_24h,
    last_run_at: runs.last_run_at,
  };
}

export async function getTopScoredListings(limit: number = 6): Promise<TopListing[]> {
  const sql = getDb();
  const rows = await sql`
    SELECT
      listing_id,
      city,
      street,
      detailed_title,
      total_rental_price,
      surface_area,
      ai_score,
      thumbnail_url,
      city_slug,
      street_slug
    FROM listings
    WHERE ai_score IS NOT NULL
    ORDER BY ai_score DESC, first_seen_at DESC
    LIMIT ${limit}
  `;
  return rows as unknown as TopListing[];
}

export async function getPricePerSqmDistribution(): Promise<PricePerSqmBucket[]> {
  const sql = getDb();
  // bucket every €5/m²
  const rows = await sql`
    SELECT
      (FLOOR((total_rental_price::numeric / surface_area) / 5) * 5)::int as bucket_start,
      (FLOOR((total_rental_price::numeric / surface_area) / 5) * 5 + 4)::int as bucket_end,
      COUNT(*)::int as count
    FROM listings
    WHERE total_rental_price > 0 AND surface_area > 0
    GROUP BY FLOOR((total_rental_price::numeric / surface_area) / 5)
    ORDER BY bucket_start
  `;
  return rows as unknown as PricePerSqmBucket[];
}
