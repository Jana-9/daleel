import { NextResponse, type NextRequest } from "next/server";

// Must match AUTH_COOKIE_NAME in the backend settings.
const SESSION_COOKIE = "daleel_session";

/**
 * Optimistic redirects based only on whether the session cookie exists.
 * This is a UX shortcut, not security: the backend validates the token on every request.
 */
export function proxy(request: NextRequest) {
  const hasSession = request.cookies.has(SESSION_COOKIE);
  const { pathname } = request.nextUrl;

  const isApp = pathname.startsWith("/dashboard") || pathname.startsWith("/chat");
  if (isApp && !hasSession) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if ((pathname === "/login" || pathname === "/register") && hasSession) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/chat/:path*", "/login", "/register"],
};
