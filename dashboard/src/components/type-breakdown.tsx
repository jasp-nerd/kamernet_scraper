"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { listingTypeLabel } from "@/lib/utils";

interface TypeBreakdownProps {
  data: { listing_type: number; count: number }[];
}

export function TypeBreakdownCard({ data }: TypeBreakdownProps) {
  const total = data.reduce((sum, d) => sum + d.count, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Listings by Type</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="text-muted-foreground text-sm">No data yet</p>
        ) : (
          <div className="space-y-3">
            {data.map((item) => {
              const pct = total > 0 ? (item.count / total) * 100 : 0;
              return (
                <div key={item.listing_type}>
                  <div className="flex justify-between text-sm mb-1">
                    <span>{listingTypeLabel(item.listing_type)}</span>
                    <span className="text-muted-foreground">
                      {item.count} ({pct.toFixed(0)}%)
                    </span>
                  </div>
                  <div className="h-2 bg-secondary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
