import { NextRequest, NextResponse } from "next/server";
import { handleProxyRequest } from "@/lib/api/proxy";

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleProxyRequest(request, params.path);
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleProxyRequest(request, params.path);
}

export async function PUT() {
  return NextResponse.json(
    { error: { code: "METHOD_NOT_ALLOWED", message: "Method PUT not allowed on BFF proxy." } },
    { status: 405 }
  );
}

export async function DELETE() {
  return NextResponse.json(
    { error: { code: "METHOD_NOT_ALLOWED", message: "Method DELETE not allowed on BFF proxy." } },
    { status: 405 }
  );
}

export async function PATCH() {
  return NextResponse.json(
    { error: { code: "METHOD_NOT_ALLOWED", message: "Method PATCH not allowed on BFF proxy." } },
    { status: 405 }
  );
}

export async function HEAD() {
  return NextResponse.json(
    { error: { code: "METHOD_NOT_ALLOWED", message: "Method HEAD not allowed on BFF proxy." } },
    { status: 405 }
  );
}
