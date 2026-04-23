// Optional password gate. In Next.js 16, what used to be called "middleware" is "proxy".
//
// If DASHBOARD_PASSWORD is set, every route except /login and static assets requires a
// cookie whose value matches the password. If DASHBOARD_PASSWORD is unset, this file is
// a no-op and the dashboard is fully open (same as before).
//
// This is deliberately minimal — intended for local use or a tiny VPS.
// For a public deployment, put this behind a real reverse proxy with proper auth.

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PASSWORD = process.env.DASHBOARD_PASSWORD;
export const COOKIE_NAME = "radar_auth";

function constantTimeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i++) {
    mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return mismatch === 0;
}

export function proxy(req: NextRequest) {
  if (!PASSWORD) return NextResponse.next();

  const cookie = req.cookies.get(COOKIE_NAME);
  if (cookie && constantTimeEqual(cookie.value, PASSWORD)) {
    return NextResponse.next();
  }

  const url = new URL("/login", req.url);
  const next = req.nextUrl.pathname + req.nextUrl.search;
  if (next && next !== "/") url.searchParams.set("next", next);
  return NextResponse.redirect(url);
}

export const config = {
  // Match everything except Next.js assets, the login page, and the login API.
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|login|api/login).*)",
  ],
};
