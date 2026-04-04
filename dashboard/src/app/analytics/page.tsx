import {
  getPriceTrends,
  getPriceDistribution,
  getTypeBreakdown,
  getStats,
} from "@/lib/queries";
import {
  PriceTrendChart,
  PriceDistributionChart,
  TypeBreakdownChart,
  NewListingsChart,
} from "@/components/price-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatPrice } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function AnalyticsPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;
  const days = params.period ? Number(params.period) : 30;

  const [priceTrends, priceDistribution, typeBreakdown, stats] =
    await Promise.all([
      getPriceTrends(days),
      getPriceDistribution(),
      getTypeBreakdown(),
      getStats(),
    ]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <div className="flex gap-2">
          {[7, 30, 90].map((d) => (
            <a
              key={d}
              href={`/analytics?period=${d}`}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                days === d
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
              }`}
            >
              {d}d
            </a>
          ))}
        </div>
      </div>

      {/* Summary */}
      <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Avg Price
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatPrice(stats.avg_price)}/mo
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Median Price
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatPrice(stats.median_price)}/mo
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Active Listings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.active_listings}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Avg Time on Market
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.avg_time_on_market_days
                ? `${stats.avg_time_on_market_days}d`
                : "N/A"}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <PriceTrendChart data={priceTrends} />

      <div className="grid gap-6 lg:grid-cols-2">
        <PriceDistributionChart data={priceDistribution} />
        <TypeBreakdownChart data={typeBreakdown} />
      </div>

      <NewListingsChart data={priceTrends} />
    </div>
  );
}
