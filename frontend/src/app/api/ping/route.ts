/** Minimal API route to verify Next dev server responds. GET /api/ping */
export async function GET() {
  return Response.json({ ok: true, t: Date.now() });
}
