"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
  BarChart,
  Bar,
  Cell,
  PieChart,
  Pie,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  formatPrice,
  listingTypeLabel,
  furnishingLabel,
  energyLabel,
  formatRelativeDate,
} from "@/lib/utils";
import type {
  CityStat,
  ScoreBucket,
  HeatmapCell,
  PriceAreaPoint,
  LandlordStat,
  EnergyStat,
  FurnishingStat,
  MarketPulse,
  TopListing,
} from "@/lib/types";

// =================================================================
// Market Pulse — top-level "vital signs" of the scraper + market
// =================================================================
export function MarketPulseCard({ pulse }: { pulse: MarketPulse }) {
  const churnPct =
    pulse.total_listings > 0
      ? Math.round((pulse.disappeared_listings / pulse.total_listings) * 100)
      : 0;

  const lastRunRelative = pulse.last_run_at
    ? formatRelativeDate(pulse.last_run_at)
    : "Never";

  // "Live" indicator is computed on the client only to avoid hydration drift
  // and to satisfy the "no impure calls during render" rule.
  const [isLive, setIsLive] = useState(false);
  useEffect(() => {
    if (!pulse.last_run_at) return;
    const compute = () => {
      const last = new Date(pulse.last_run_at!).getTime();
      setIsLive(Date.now() - last < 5 * 60 * 1000);
    };
    compute();
    const id = setInterval(compute, 30_000);
    return () => clearInterval(id);
  }, [pulse.last_run_at]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Market Pulse</CardTitle>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                isLive ? "bg-green-500 animate-pulse" : "bg-muted-foreground/40"
              }`}
            />
            {isLive ? "Live" : `Last run ${lastRunRelative}`}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <PulseMetric
            label="Total Tracked"
            value={pulse.total_listings.toString()}
            sub={`${pulse.active_listings} live now`}
          />
          <PulseMetric
            label="New (24h)"
            value={pulse.new_24h.toString()}
            sub={`${pulse.gone_24h} disappeared`}
            accent={pulse.new_24h > 0 ? "green" : undefined}
          />
          <PulseMetric
            label="Median Lifespan"
            value={
              pulse.median_lifespan_hours != null
                ? formatHours(pulse.median_lifespan_hours)
                : "N/A"
            }
            sub={
              pulse.avg_lifespan_hours != null
                ? `avg ${formatHours(pulse.avg_lifespan_hours)}`
                : ""
            }
          />
          <PulseMetric
            label="Churn Rate"
            value={`${churnPct}%`}
            sub={`${pulse.scrape_runs_24h} scrapes / 24h`}
          />
        </div>
      </CardContent>
    </Card>
  );
}

function PulseMetric({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: "green" | "red";
}) {
  const accentColor =
    accent === "green"
      ? "text-green-600"
      : accent === "red"
        ? "text-red-500"
        : "";
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className={`text-2xl font-bold tabular-nums ${accentColor}`}>
        {value}
      </span>
      {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
    </div>
  );
}

function formatHours(h: number): string {
  if (h < 1) return `${Math.round(h * 60)}m`;
  if (h < 24) return `${h.toFixed(1)}h`;
  return `${(h / 24).toFixed(1)}d`;
}

// =================================================================
// City Leaderboard — bar table with avg price + €/m²
// =================================================================
export function CityLeaderboard({ cities }: { cities: CityStat[] }) {
  if (cities.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Top Cities</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm py-8 text-center">
            No data
          </p>
        </CardContent>
      </Card>
    );
  }

  const max = Math.max(...cities.map((c) => c.count));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Top Cities</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {cities.map((city, i) => {
            const pct = (city.count / max) * 100;
            return (
              <div key={city.city} className="space-y-1">
                <div className="flex items-baseline justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground tabular-nums w-4">
                      {i + 1}
                    </span>
                    <span className="font-medium">{city.city}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground tabular-nums">
                    <span>{formatPrice(city.avg_price)}/mo</span>
                    {city.avg_price_per_sqm != null && (
                      <span>€{city.avg_price_per_sqm}/m²</span>
                    )}
                    <span className="font-semibold text-foreground">
                      {city.count}
                    </span>
                  </div>
                </div>
                <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-foreground/80"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// =================================================================
// Score Distribution — colored buckets + radial summary
// =================================================================
export function ScoreDistribution({ buckets }: { buckets: ScoreBucket[] }) {
  if (buckets.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            AI Score Distribution
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm py-8 text-center">
            No scored listings yet
          </p>
        </CardContent>
      </Card>
    );
  }

  // Ensure all 5 buckets exist
  const allBuckets = [
    { bucket: "0-19", min_score: 0, max_score: 19 },
    { bucket: "20-39", min_score: 20, max_score: 39 },
    { bucket: "40-59", min_score: 40, max_score: 59 },
    { bucket: "60-79", min_score: 60, max_score: 79 },
    { bucket: "80-100", min_score: 80, max_score: 100 },
  ].map((b) => {
    const found = buckets.find((x) => x.bucket === b.bucket);
    return { ...b, count: found?.count ?? 0 };
  });

  const total = allBuckets.reduce((acc, b) => acc + b.count, 0);
  const max = Math.max(...allBuckets.map((b) => b.count), 1);

  const colors = [
    "rgb(239, 68, 68)", // red
    "rgb(249, 115, 22)", // orange
    "rgb(234, 179, 8)", // yellow
    "rgb(132, 204, 22)", // lime
    "rgb(34, 197, 94)", // green
  ];

  // % at or above 60 (telegram threshold-ish)
  const goodCount =
    (allBuckets[3]?.count ?? 0) + (allBuckets[4]?.count ?? 0);
  const goodPct = total > 0 ? Math.round((goodCount / total) * 100) : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">
          AI Score Distribution
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-6 md:grid-cols-[1fr_auto] items-center">
          <div className="space-y-2">
            {allBuckets.map((b, i) => {
              const pct = (b.count / max) * 100;
              const sharePct =
                total > 0 ? Math.round((b.count / total) * 100) : 0;
              return (
                <div key={b.bucket} className="space-y-1">
                  <div className="flex items-baseline justify-between text-xs">
                    <span className="font-medium">{b.bucket}</span>
                    <span className="text-muted-foreground tabular-nums">
                      {b.count} · {sharePct}%
                    </span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${pct}%`,
                        backgroundColor: colors[i],
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex flex-col items-center gap-1">
            <div className="relative">
              <ResponsiveContainer width={130} height={130}>
                <RadialBarChart
                  innerRadius="70%"
                  outerRadius="100%"
                  data={[{ name: "good", value: goodPct }]}
                  startAngle={90}
                  endAngle={-270}
                >
                  <PolarAngleAxis
                    type="number"
                    domain={[0, 100]}
                    tick={false}
                  />
                  <RadialBar
                    background={{ fill: "var(--muted)" }}
                    dataKey="value"
                    cornerRadius={8}
                    fill="rgb(34, 197, 94)"
                  />
                </RadialBarChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-2xl font-bold tabular-nums">
                  {goodPct}%
                </span>
              </div>
            </div>
            <span className="text-xs text-muted-foreground text-center">
              scored ≥ 60
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// =================================================================
// Hourly Heatmap — day-of-week × hour
// =================================================================
export function HourlyHeatmap({ data }: { data: HeatmapCell[] }) {
  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const hours = Array.from({ length: 24 }, (_, i) => i);

  // Build a matrix [dow][hour] = count
  const matrix: number[][] = days.map(() => hours.map(() => 0));
  let max = 0;
  for (const cell of data) {
    if (cell.dow >= 0 && cell.dow < 7 && cell.hour >= 0 && cell.hour < 24) {
      matrix[cell.dow][cell.hour] = cell.count;
      if (cell.count > max) max = cell.count;
    }
  }

  // Best hour overall (sum across all days)
  const hourTotals = hours.map((h) =>
    matrix.reduce((acc, row) => acc + row[h], 0),
  );
  const peakHour = hourTotals.indexOf(Math.max(...hourTotals));

  const intensityColor = (count: number): string => {
    if (count === 0) return "var(--muted)";
    const ratio = count / max;
    // monochrome opacity scale on foreground
    const opacity = 0.15 + ratio * 0.85;
    return `oklch(0.205 0 0 / ${opacity})`;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-baseline justify-between">
          <CardTitle className="text-sm font-medium">
            When listings appear
          </CardTitle>
          <span className="text-xs text-muted-foreground">
            Peak: {peakHour}:00
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <div className="inline-block min-w-full">
            {/* hour labels (top) */}
            <div className="flex gap-[2px] pl-8 mb-1">
              {hours.map((h) => (
                <div
                  key={h}
                  className="w-4 text-[9px] text-muted-foreground text-center"
                >
                  {h % 3 === 0 ? h : ""}
                </div>
              ))}
            </div>
            {days.map((day, i) => (
              <div key={day} className="flex items-center gap-[2px] mb-[2px]">
                <div className="w-7 text-[10px] text-muted-foreground text-right pr-1">
                  {day}
                </div>
                {hours.map((h) => {
                  const count = matrix[i][h];
                  return (
                    <div
                      key={h}
                      title={`${day} ${h}:00 — ${count} listing${count !== 1 ? "s" : ""}`}
                      className="w-4 h-4 rounded-sm"
                      style={{ backgroundColor: intensityColor(count) }}
                    />
                  );
                })}
              </div>
            ))}
          </div>
        </div>
        <p className="text-xs text-muted-foreground mt-3">
          Darker squares = more new listings first appeared in that hour. Use
          this to know when to refresh.
        </p>
      </CardContent>
    </Card>
  );
}

// =================================================================
// Price vs Area Scatter — efficiency map with median guideline
// =================================================================
export function PriceAreaScatter({ points }: { points: PriceAreaPoint[] }) {
  if (points.length === 0) return null;

  // Compute median €/m² for the diagonal "fair price" line
  const ratios = points
    .map((p) => p.price / p.area)
    .sort((a, b) => a - b);
  const medianRatio = ratios[Math.floor(ratios.length / 2)];

  const grouped = [
    {
      type: "Room",
      data: points.filter((p) => p.type === 1),
      color: "rgb(99, 102, 241)",
    },
    {
      type: "Apartment",
      data: points.filter((p) => p.type === 2),
      color: "rgb(34, 197, 94)",
    },
    {
      type: "Studio",
      data: points.filter((p) => p.type === 3 || p.type === 4),
      color: "rgb(249, 115, 22)",
    },
  ].filter((g) => g.data.length > 0);

  // Build the diagonal reference line as a fake series
  const minArea = Math.min(...points.map((p) => p.area));
  const maxArea = Math.max(...points.map((p) => p.area));
  const refLine = [
    { area: minArea, price: minArea * medianRatio },
    { area: maxArea, price: maxArea * medianRatio },
  ];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-baseline justify-between">
          <CardTitle className="text-sm font-medium">
            Price vs Surface Area
          </CardTitle>
          <span className="text-xs text-muted-foreground">
            Median €{medianRatio.toFixed(0)}/m²
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={320}>
          <ScatterChart margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis
              type="number"
              dataKey="area"
              name="Area"
              unit=" m²"
              tick={{ fontSize: 11 }}
              domain={["dataMin - 5", "dataMax + 5"]}
            />
            <YAxis
              type="number"
              dataKey="price"
              name="Price"
              unit="€"
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `${v}`}
            />
            <ZAxis range={[40, 40]} />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              content={({ active, payload }) => {
                if (!active || !payload || payload.length === 0) return null;
                const p = payload[0].payload as PriceAreaPoint;
                return (
                  <div className="rounded-md border bg-background p-2 text-xs shadow-sm">
                    <div className="font-medium">
                      {p.street ?? `#${p.listing_id}`}
                    </div>
                    <div className="text-muted-foreground">
                      {p.city ?? ""} · {listingTypeLabel(p.type)}
                    </div>
                    <div className="mt-1 tabular-nums">
                      {formatPrice(p.price)}/mo · {p.area} m²
                    </div>
                    <div className="text-muted-foreground tabular-nums">
                      €{(p.price / p.area).toFixed(0)}/m²
                    </div>
                  </div>
                );
              }}
            />
            {/* Median ratio reference line */}
            <Scatter
              data={refLine}
              line={{ stroke: "var(--muted-foreground)", strokeDasharray: "4 4" }}
              shape={() => <g />}
              legendType="none"
            />
            {grouped.map((g) => (
              <Scatter
                key={g.type}
                name={g.type}
                data={g.data}
                fill={g.color}
                fillOpacity={0.7}
              />
            ))}
            <Legend
              wrapperStyle={{ fontSize: 11 }}
              iconType="circle"
              iconSize={8}
            />
          </ScatterChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground mt-2">
          Dots below the dashed line are cheaper than the median €/m². Each dot
          is a listing — hover for details.
        </p>
      </CardContent>
    </Card>
  );
}

// =================================================================
// Top Scored Listings showcase
// =================================================================
export function TopScoredShowcase({ listings }: { listings: TopListing[] }) {
  if (listings.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Top Scored Listings
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm py-8 text-center">
            No scored listings yet
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Top Scored Listings</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {listings.map((l) => (
            <Link
              key={l.listing_id}
              href={`/listings/${l.listing_id}`}
              className="group relative overflow-hidden rounded-lg border bg-card hover:shadow-md transition-shadow"
            >
              <div
                className="aspect-[4/3] bg-muted relative"
                style={
                  l.thumbnail_url
                    ? {
                        backgroundImage: `url(${l.thumbnail_url})`,
                        backgroundSize: "cover",
                        backgroundPosition: "center",
                      }
                    : undefined
                }
              >
                <div className="absolute top-2 right-2">
                  <ScoreBadge score={l.ai_score} />
                </div>
                <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-black/70 to-transparent" />
                <div className="absolute inset-x-0 bottom-0 p-2 text-white">
                  <div className="text-xs font-medium tabular-nums">
                    {formatPrice(l.total_rental_price)}
                    {l.surface_area && (
                      <span className="opacity-80"> · {l.surface_area} m²</span>
                    )}
                  </div>
                </div>
              </div>
              <div className="p-2">
                <div className="text-xs font-medium line-clamp-1 group-hover:underline">
                  {l.street ?? l.detailed_title ?? `Listing #${l.listing_id}`}
                </div>
                <div className="text-[10px] text-muted-foreground line-clamp-1">
                  {l.city ?? ""}
                </div>
              </div>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 70
      ? "bg-green-500"
      : score >= 40
        ? "bg-yellow-500"
        : "bg-red-500";
  return (
    <div
      className={`${color} text-white text-xs font-bold tabular-nums rounded-full h-7 w-7 flex items-center justify-center shadow-md ring-2 ring-white/40`}
    >
      {score}
    </div>
  );
}

// =================================================================
// Landlord leaderboard
// =================================================================
export function LandlordLeaderboard({
  landlords,
}: {
  landlords: LandlordStat[];
}) {
  if (landlords.length === 0) return null;

  const max = Math.max(...landlords.map((l) => l.count));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Most Active Landlords</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {landlords.map((l, i) => {
            const pct = (l.count / max) * 100;
            return (
              <div
                key={`${l.landlord_name}-${i}`}
                className="flex items-center gap-3 text-sm"
              >
                <span className="text-xs text-muted-foreground tabular-nums w-4">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="font-medium truncate">
                      {l.landlord_name}
                      {l.verified && (
                        <span
                          className="ml-1 inline-block text-[10px] align-middle text-green-600"
                          title="Verified"
                        >
                          ✓
                        </span>
                      )}
                    </span>
                    <span className="text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                      {formatPrice(l.avg_price)} avg
                    </span>
                  </div>
                  <div className="h-1 w-full rounded-full bg-muted overflow-hidden mt-1">
                    <div
                      className="h-full bg-foreground/70 rounded-full"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
                <span className="text-xs font-semibold tabular-nums w-6 text-right">
                  {l.count}
                </span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// =================================================================
// Energy label distribution — horizontal bars
// =================================================================
export function EnergyLabelChart({ data }: { data: EnergyStat[] }) {
  if (data.length === 0) return null;

  const labelColor = (id: number | null) => {
    if (id == null) return "rgb(156, 163, 175)";
    if (id <= 2) return "rgb(34, 197, 94)"; // A++ A+++
    if (id <= 4) return "rgb(132, 204, 22)"; // A+ A
    if (id <= 6) return "rgb(234, 179, 8)"; // B C
    if (id <= 8) return "rgb(249, 115, 22)"; // D E
    return "rgb(239, 68, 68)"; // F G
  };

  const chartData = data.map((d) => ({
    label: d.energy_label_id != null ? energyLabel(d.energy_label_id) : "?",
    count: d.count,
    avg_price: d.avg_price,
    fill: labelColor(d.energy_label_id),
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Energy Labels</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ left: 8, right: 8, top: 0, bottom: 0 }}
          >
            <CartesianGrid horizontal={false} strokeDasharray="3 3" opacity={0.3} />
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis
              type="category"
              dataKey="label"
              tick={{ fontSize: 11 }}
              width={36}
            />
            <Tooltip
              formatter={(value, name) => {
                if (name === "count") return [value, "Listings"];
                return [`€${value}`, "Avg Price"];
              }}
            />
            <Bar dataKey="count" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// =================================================================
// Furnishing donut
// =================================================================
export function FurnishingDonut({ data }: { data: FurnishingStat[] }) {
  if (data.length === 0) return null;

  const COLORS = [
    "oklch(0.205 0 0)",
    "oklch(0.439 0 0)",
    "oklch(0.708 0 0)",
    "oklch(0.87 0 0)",
  ];

  const chartData = data.map((d) => ({
    name: furnishingLabel(d.furnishing_id),
    value: d.count,
    avg_price: d.avg_price,
  }));

  const total = chartData.reduce((acc, d) => acc + d.value, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Furnishing Mix</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={chartData}
                dataKey="value"
                nameKey="name"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={2}
              >
                {chartData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value, name, item) => {
                  const ap = item?.payload?.avg_price;
                  return [
                    `${value} listings · €${ap}/mo avg`,
                    name as string,
                  ];
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-2xl font-bold tabular-nums">{total}</span>
            <span className="text-xs text-muted-foreground">total</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 justify-center mt-2">
          {chartData.map((d, i) => (
            <div key={d.name} className="flex items-center gap-1.5 text-xs">
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: COLORS[i % COLORS.length] }}
              />
              <span>{d.name}</span>
              <span className="text-muted-foreground tabular-nums">
                {d.value}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
