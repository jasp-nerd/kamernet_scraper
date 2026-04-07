import { NextRequest, NextResponse } from "next/server";
import { getListings } from "@/lib/queries";
import type { ListingsFilter } from "@/lib/types";

export async function GET(request: NextRequest) {
  const sp = request.nextUrl.searchParams;

  const filters: ListingsFilter = {
    page: sp.has("page") ? Number(sp.get("page")) : 1,
    limit: sp.has("limit") ? Math.min(Number(sp.get("limit")), 100) : 20,
    sort: sp.get("sort") ?? "first_seen_at",
    order: (sp.get("order") as "asc" | "desc") ?? "desc",
  };

  if (sp.has("minPrice")) filters.minPrice = Number(sp.get("minPrice"));
  if (sp.has("maxPrice")) filters.maxPrice = Number(sp.get("maxPrice"));
  if (sp.has("type")) filters.type = Number(sp.get("type"));
  if (sp.has("furnishing")) filters.furnishing = Number(sp.get("furnishing"));
  if (sp.has("minArea")) filters.minArea = Number(sp.get("minArea"));
  if (sp.has("maxArea")) filters.maxArea = Number(sp.get("maxArea"));
  if (sp.get("active") === "true") filters.active = true;
  if (sp.get("active") === "false") filters.active = false;
  if (sp.has("minScore")) filters.minScore = Number(sp.get("minScore"));

  const result = await getListings(filters);
  return NextResponse.json(result);
}
