"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";

export function FilterBar() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const updateParam = useCallback(
    (key: string, value: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value && value !== "all") {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      params.delete("page");
      router.push(`/listings?${params.toString()}`);
    },
    [router, searchParams]
  );

  const clearFilters = useCallback(() => {
    router.push("/listings");
  }, [router]);

  return (
    <div className="flex flex-wrap gap-3 items-end">
      <div>
        <label className="text-xs text-muted-foreground mb-1 block">
          Min Price
        </label>
        <Input
          type="number"
          placeholder="€ min"
          className="w-28"
          defaultValue={searchParams.get("minPrice") ?? ""}
          onBlur={(e) => updateParam("minPrice", e.target.value)}
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground mb-1 block">
          Max Price
        </label>
        <Input
          type="number"
          placeholder="€ max"
          className="w-28"
          defaultValue={searchParams.get("maxPrice") ?? ""}
          onBlur={(e) => updateParam("maxPrice", e.target.value)}
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground mb-1 block">Type</label>
        <Select
          defaultValue={searchParams.get("type") ?? "all"}
          onValueChange={(v) => updateParam("type", v)}
        >
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            <SelectItem value="1">Room</SelectItem>
            <SelectItem value="2">Apartment</SelectItem>
            <SelectItem value="3">Studio</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <label className="text-xs text-muted-foreground mb-1 block">
          Furnishing
        </label>
        <Select
          defaultValue={searchParams.get("furnishing") ?? "all"}
          onValueChange={(v) => updateParam("furnishing", v)}
        >
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="1">Unfurnished</SelectItem>
            <SelectItem value="3">Semi-furnished</SelectItem>
            <SelectItem value="4">Furnished</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <label className="text-xs text-muted-foreground mb-1 block">Sort</label>
        <Select
          defaultValue={searchParams.get("sort") ?? "first_seen_at"}
          onValueChange={(v) => updateParam("sort", v)}
        >
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="first_seen_at">Newest</SelectItem>
            <SelectItem value="total_rental_price">Price</SelectItem>
            <SelectItem value="surface_area">Area</SelectItem>
            <SelectItem value="ai_score">AI Score</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <label className="text-xs text-muted-foreground mb-1 block">
          Min Score
        </label>
        <Input
          type="number"
          placeholder="0-100"
          className="w-24"
          defaultValue={searchParams.get("minScore") ?? ""}
          onBlur={(e) => updateParam("minScore", e.target.value)}
        />
      </div>
      <Button variant="outline" size="sm" onClick={clearFilters}>
        Clear
      </Button>
    </div>
  );
}
