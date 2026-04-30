import fs from "node:fs";

function readEnv(filePath) {
  return Object.fromEntries(
    fs.readFileSync(filePath, "utf8")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#") && line.includes("="))
      .map((line) => {
        const index = line.indexOf("=");
        return [line.slice(0, index).trim(), line.slice(index + 1).trim()];
      }),
  );
}

const env = readEnv(".env.supabase.local");
const supabaseUrl = (env.SUPABASE_URL || env.NEXT_PUBLIC_SUPABASE_URL || "").replace(/\/$/, "");
const anonKey = env.SUPABASE_ANON_KEY || env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !anonKey) {
  throw new Error("Missing Supabase URL or anon key in .env.supabase.local");
}

async function request(path) {
  const response = await fetch(`${supabaseUrl}${path}`, {
    headers: {
      apikey: anonKey,
      Authorization: `Bearer ${anonKey}`,
    },
  });
  const text = await response.text();
  return {
    ok: response.ok,
    status: response.status,
    statusText: response.statusText,
    bodyPreview: text.slice(0, 220),
  };
}

const checks = [
  ["/auth/v1/settings", "Auth settings"],
  ["/rest/v1/floatvocab_profiles?select=*&limit=1", "FloatVocab profiles table"],
  ["/rest/v1/floatvocab_sync_state?select=*&limit=1", "FloatVocab sync table"],
];

for (const [path, label] of checks) {
  const result = await request(path);
  console.log(JSON.stringify({ label, ...result }, null, 2));
}
