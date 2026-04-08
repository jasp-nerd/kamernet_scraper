import {
  getPriceTrends,
  getPriceDistribution,
  getTypeBreakdown,
  getStats,
  getCityStats,
  getScoreDistribution,
  getHourlyHeatmap,
  getPriceAreaScatter,
  getLandlordStats,
  getEnergyStats,
  getFurnishingStats,
  getMarketPulse,
  getTopScoredListings,
} from "@/lib/queries";
import {
  PriceTrendChart,
  PriceDistributionChart,
  TypeBreakdownChart,
  NewListingsChart,
} from "@/components/price-chart";
import {
  MarketPulseCard,
  CityLeaderboard,
  ScoreDistribution,
  HourlyHeatmap,
  PriceAreaScatter,
  TopScoredShowcase,
  LandlordLeaderboard,
  EnergyLabelChart,
  FurnishingDonut,
} from "@/components/analytics-widgets";
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

  const [
    priceTrends,
    priceDistribution,
    typeBreakdown,
    stats,
    cityStats,
    scoreBuckets,
    heatmap,
    scatter,
    landlords,
    energyStats,
    furnishingStats,
    marketPulse,
    topScored,
  ] = await Promise.all([
    getPriceTrends(days),
    getPriceDistribution(),
    getTypeBreakdown(),
    getStats(),
    getCityStats(10),
    getScoreDistribution(),
    getHourlyHeatmap(),
    getPriceAreaScatter(500),
    getLandlordStats(8),
    getEnergyStats(),
    getFurnishingStats(),
    getMarketPulse(),
    getTopScoredListings(6),
  ]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">Analytics</h1>
          <p className="text-xs text-muted-foreground mt-1">
            Across all {stats.total_listings} tracked listings
          </p>
        </div>
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

      {/* Market pulse — vital signs */}
      <MarketPulseCard pulse={marketPulse} />

      {/* Headline numbers */}
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
              Avg Area
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.avg_area ? `${stats.avg_area} m²` : "N/A"}
            </div>
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

      {/* Time-series */}
      <PriceTrendChart data={priceTrends} />

      {/* AI scoring + showcase */}
      <div className="grid gap-6 lg:grid-cols-2">
        <ScoreDistribution buckets={scoreBuckets} />
        <TopScoredShowcase listings={topScored} />
      </div>

      {/* Scatter (full width) */}
      <PriceAreaScatter points={scatter} />

      {/* Cities + heatmap */}
      <div className="grid gap-6 lg:grid-cols-2">
        <CityLeaderboard cities={cityStats} />
        <HourlyHeatmap data={heatmap} />
      </div>

      {/* Distributions */}
      <div className="grid gap-6 lg:grid-cols-2">
        <PriceDistributionChart data={priceDistribution} />
        <TypeBreakdownChart data={typeBreakdown} />
      </div>

      {/* Energy + furnishing + landlords */}
      <div className="grid gap-6 lg:grid-cols-3">
        <EnergyLabelChart data={energyStats} />
        <FurnishingDonut data={furnishingStats} />
        <LandlordLeaderboard landlords={landlords} />
      </div>

      <NewListingsChart data={priceTrends} />
    </div>
  );
}
