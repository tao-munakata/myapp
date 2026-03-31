import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";

export async function POST(req: NextRequest): Promise<NextResponse> {
  const formData = await req.formData();

  const res = await fetch(`${BACKEND_URL}/api/process`, {
    method: "POST",
    body: formData,
  }).catch(() => null);

  if (!res) {
    return NextResponse.json(
      { detail: "バックエンドに接続できません" },
      { status: 502 }
    );
  }

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
