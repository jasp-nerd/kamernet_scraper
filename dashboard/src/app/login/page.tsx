import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; error?: string }>;
}) {
  const params = await searchParams;
  const next = params.next ?? "/";

  if (!process.env.DASHBOARD_PASSWORD) {
    // Auth disabled — don't linger on the login page
    redirect(next);
  }

  return (
    <div className="mx-auto mt-16 w-full max-w-sm px-6">
      <h1 className="text-2xl font-semibold mb-1">Sign in</h1>
      <p className="text-sm text-muted-foreground mb-6">
        This dashboard is password-protected.
      </p>
      <form method="POST" action="/api/login" className="space-y-3">
        <input type="hidden" name="next" value={next} />
        <input
          type="password"
          name="password"
          placeholder="Password"
          required
          autoFocus
          className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
        <button
          type="submit"
          className="w-full rounded-md bg-foreground text-background py-2 text-sm font-medium hover:opacity-90"
        >
          Sign in
        </button>
        {params.error ? (
          <p className="text-sm text-red-600">Incorrect password.</p>
        ) : null}
      </form>
    </div>
  );
}
