import { NextRequest, NextResponse } from "next/server";
import {
  getPriceTrends,
  getPriceDistribution,
  getTypeBreakdown,
} from "@/lib/queries";

export async function GET(request: NextRequest) {
  const sp = request.nextUrl.searchParams;
  const days = sp.has("period") ? Number(sp.get("period")) : 30;

  const [priceTrends, priceDistribution, typeBreakdown] = await Promise.all([
    getPriceTrends(days),
    getPriceDistribution(),
    getTypeBreakdown(),
  ]);

  return NextResponse.json({
    priceTrends,
    priceDistribution,
    typeBreakdown,
  });
}
