// アプリに同梱するものだけを dist/ へ集める。
//
// リポジトリ直下をそのまま同梱先にはできない。manual.html や docs/images が
// 入ってしまい、docs/images だけで 6.5MB ある。アプリの動作には要らない。
//
// Windows のランナーでも動くよう、シェルではなく Node で書いてある。

import { cp, rm, mkdir, stat, readdir } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, "../..");   // desktop/scripts → リポジトリ直下
const dist = resolve(here, "../dist");

// index.html は skin.jpg を url() で参照し、presets/*.wav を fetch する。
// この3つが揃っていないと、起動はしても背景とプリセットが欠ける。
const ITEMS = ["index.html", "skin.jpg", "presets"];

await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });

let total = 0;
for (const name of ITEMS) {
  const from = join(repo, name);
  try {
    await stat(from);
  } catch {
    // 静かに欠けるのがいちばん困る。ここで止める。
    console.error(`同梱物が見つかりません: ${name}`);
    process.exit(1);
  }
  await cp(from, join(dist, name), { recursive: true });
  total += await sizeOf(join(dist, name));
}

console.log(`dist/ を用意しました (${(total / 1024 / 1024).toFixed(1)} MB)`);
for (const name of ITEMS) console.log(`  ${name}`);

async function sizeOf(path) {
  const s = await stat(path);
  if (!s.isDirectory()) return s.size;
  let n = 0;
  for (const entry of await readdir(path)) n += await sizeOf(join(path, entry));
  return n;
}
