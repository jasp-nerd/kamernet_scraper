import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatsCards } from "@/components/stats-cards";
import { RecentListings } from "@/components/recent-listings";
import { TypeBreakdownCard } from "@/components/type-breakdown";
import { getStats, getRecentListings } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [stats, recentListings] = await Promise.all([
    getStats(),
    getRecentListings(10),
  ]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <StatsCards stats={stats} />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent Listings</CardTitle>
          </CardHeader>
          <CardContent>
            <RecentListings listings={recentListings} />
          </CardContent>
        </Card>

        <TypeBreakdownCard data={stats.listings_by_type} />
      </div>
    </div>
  );
}
