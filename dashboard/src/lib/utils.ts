import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPrice(price: number | null): string {
  if (!price) return "N/A";
  return `€${price.toLocaleString("nl-NL")}`;
}

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return "N/A";
  return new Date(dateStr).toLocaleDateString("nl-NL", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatRelativeDate(dateStr: string | null): string {
  if (!dateStr) return "N/A";
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return formatDate(dateStr);
}

const TYPE_MAP: Record<number, string> = {
  1: "Room",
  2: "Apartment",
  3: "Studio",
  4: "Studio",
};

export function listingTypeLabel(type: number | null): string {
  if (!type) return "Unknown";
  return TYPE_MAP[type] ?? "Unknown";
}

const FURNISHING_MAP: Record<number, string> = {
  1: "Unfurnished",
  2: "Unfurnished",
  3: "Semi-furnished",
  4: "Furnished",
};

export function furnishingLabel(id: number | null): string {
  if (!id) return "Unknown";
  return FURNISHING_MAP[id] ?? "Unknown";
}

const ENERGY_MAP: Record<number, string> = {
  1: "A+++",
  2: "A++",
  3: "A+",
  4: "A",
  5: "B",
  6: "C",
  7: "D",
  8: "E",
  9: "F",
  10: "G",
};

export function energyLabel(id: number | null): string {
  if (!id) return "N/A";
  return ENERGY_MAP[id] ?? "N/A";
}
