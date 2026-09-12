import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const AUTH_COOKIE = "bizzai_token";

const protectedPrefixes = [
  "/overview",
  "/customers",
  "/segments",
  "/opportunities",
  "/predictions",
  "/insights",
  "/data",
  "/alerts",
  "/reports",
  "/settings",
];

/**
 * Cookie-presence gate. The backend remains authoritative: expired or
 * tampered tokens still fail /me and the client guard signs the user out.
 */
export function middleware(request: NextRequest) {
  const token = request.cookies.get(AUTH_COOKIE)?.value;
  const { pathname } = request.nextUrl;

  const isProtected = protectedPrefixes.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );
  const isAuthPage = pathname === "/login" || pathname === "/register";

  if (isProtected && token == null) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (isAuthPage && token != null) {
    return NextResponse.redirect(new URL("/overview", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/overview/:path*",
    "/customers/:path*",
    "/segments/:path*",
    "/opportunities/:path*",
    "/predictions/:path*",
    "/insights/:path*",
    "/data/:path*",
    "/alerts/:path*",
    "/reports/:path*",
    "/settings/:path*",
    "/login",
    "/register",
  ],
};
