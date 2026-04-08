export interface Listing {
  listing_id: number;
  street: string | null;
  city: string | null;
  city_slug: string | null;
  street_slug: string | null;
  postal_code: string | null;
  house_number: string | null;
  house_number_addition: string | null;
  listing_type: number | null;
  furnishing_id: number | null;
  total_rental_price: number | null;
  surface_area: number | null;
  deposit: number | null;
  utilities_included: boolean | null;
  num_bedrooms: number | null;
  num_rooms: number | null;
  energy_label_id: number | null;
  pets_allowed: boolean | null;
  smoking_allowed: boolean | null;
  registration_allowed: boolean | null;
  min_age: number | null;
  max_age: number | null;
  suitable_for_persons: number | null;
  availability_start: string | null;
  availability_end: string | null;
  detailed_title: string | null;
  detailed_description: string | null;
  thumbnail_url: string | null;
  full_preview_image_url: string | null;
  additional_images: string[] | null;
  landlord_name: string | null;
  landlord_verified: boolean;
  landlord_response_rate: number | null;
  landlord_response_time: string | null;
  landlord_member_since: string | null;
  landlord_last_seen: string | null;
  landlord_active_listings: number | null;
  create_date: string | null;
  publish_date: string | null;
  first_seen_at: string;
  last_seen_at: string;
  disappeared_at: string | null;
  is_new_advert: boolean;
  is_top_advert: boolean;
  updated_at: string;
  ai_score: number | null;
  ai_score_reasoning: string | null;
}

export interface Stats {
  total_listings: number;
  active_listings: number;
  avg_price: number;
  median_price: number;
  avg_area: number;
  new_today: number;
  avg_time_on_market_days: number | null;
  listings_by_type: { listing_type: number; count: number }[];
  listings_by_furnishing: { furnishing_id: number; count: number }[];
}

export interface PriceTrend {
  date: string;
  avg_price: number;
  count: number;
}

export interface PriceDistribution {
  bucket_start: number;
  bucket_end: number;
  count: number;
}

export interface TypeBreakdown {
  listing_type: number;
  count: number;
  avg_price: number;
}

export interface CityStat {
  city: string;
  count: number;
  avg_price: number;
  median_price: number;
  avg_area: number;
  avg_price_per_sqm: number | null;
}

export interface ScoreBucket {
  bucket: string;
  count: number;
  min_score: number;
  max_score: number;
}

export interface HeatmapCell {
  dow: number;
  hour: number;
  count: number;
}

export interface PriceAreaPoint {
  listing_id: number;
  price: number;
  area: number;
  type: number | null;
  score: number | null;
  city: string | null;
  street: string | null;
}

export interface LandlordStat {
  landlord_name: string;
  count: number;
  verified: boolean;
  avg_price: number;
  avg_score: number | null;
}

export interface EnergyStat {
  energy_label_id: number | null;
  count: number;
  avg_price: number;
}

export interface FurnishingStat {
  furnishing_id: number | null;
  count: number;
  avg_price: number;
}

export interface MarketPulse {
  total_listings: number;
  active_listings: number;
  disappeared_listings: number;
  avg_lifespan_hours: number | null;
  median_lifespan_hours: number | null;
  scrape_runs_24h: number;
  new_24h: number;
  gone_24h: number;
  last_run_at: string | null;
}

export interface TopListing {
  listing_id: number;
  city: string | null;
  street: string | null;
  detailed_title: string | null;
  total_rental_price: number | null;
  surface_area: number | null;
  ai_score: number;
  thumbnail_url: string | null;
  city_slug: string | null;
  street_slug: string | null;
}

export interface PricePerSqmBucket {
  bucket_start: number;
  bucket_end: number;
  count: number;
}

export interface AllPriceTrend {
  date: string;
  avg_price: number;
  count: number;
  cumulative: number;
}

export interface ListingsFilter {
  page?: number;
  limit?: number;
  minPrice?: number;
  maxPrice?: number;
  type?: number;
  furnishing?: number;
  minArea?: number;
  maxArea?: number;
  sort?: string;
  order?: "asc" | "desc";
  active?: boolean;
  minScore?: number;
}
