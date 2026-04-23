import { NextResponse } from "next/server";

const COOKIE_NAME = "radar_auth";
const THIRTY_DAYS = 60 * 60 * 24 * 30;

export async function POST(request: Request) {
  const expected = process.env.DASHBOARD_PASSWORD;
  const formData = await request.formData();
  const password = String(formData.get("password") ?? "");
  const next = String(formData.get("next") ?? "/") || "/";

  if (!expected || password !== expected) {
    const url = new URL("/login", request.url);
    url.searchParams.set("error", "1");
    if (next !== "/") url.searchParams.set("next", next);
    return NextResponse.redirect(url, { status: 303 });
  }

  const response = NextResponse.redirect(new URL(next, request.url), { status: 303 });
  response.cookies.set(COOKIE_NAME, expected, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: THIRTY_DAYS,
  });
  return response;
}
