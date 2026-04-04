import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Stats } from "@/lib/types";
import { formatPrice } from "@/lib/utils";

export function StatsCards({ stats }: { stats: Stats }) {
  const cards = [
    { title: "Active Listings", value: stats.active_listings.toString() },
    { title: "Total Tracked", value: stats.total_listings.toString() },
    { title: "Avg Price", value: formatPrice(stats.avg_price) + "/mo" },
    { title: "Median Price", value: formatPrice(stats.median_price) + "/mo" },
    { title: "Avg Area", value: stats.avg_area ? `${stats.avg_area} m²` : "N/A" },
    { title: "New Today", value: stats.new_today.toString() },
    {
      title: "Avg Time on Market",
      value: stats.avg_time_on_market_days
        ? `${stats.avg_time_on_market_days} days`
        : "N/A",
    },
  ];

  return (
    <div className="grid gap-4 grid-cols-2 md:grid-cols-4 lg:grid-cols-7">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {card.title}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{card.value}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
