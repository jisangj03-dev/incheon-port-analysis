// 발행본은 저장소 자리 그대로 읽는다 — 사본을 만들지 않는다(소스가 둘이면 갈라진다 · 사고 31).
// id 는 파일 이름 그대로(확장자만 뺀다) — 지면 주소가 Jekyll 때와 같아야 한다(기존 주소 유지).
import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";

const keepName = ({ entry }: { entry: string }) => entry.replace(/\.md$/i, "");

export const collections = {
  reports: defineCollection({ loader: glob({ pattern: "*.md", base: "../reports", generateId: keepName }) }),
  docs: defineCollection({ loader: glob({ pattern: "**/*.md", base: "../docs", generateId: keepName }) }),
  analysis: defineCollection({ loader: glob({ pattern: ["**/*.md", "!**/_*.md", "!site_qa/**"], base: "../analysis", generateId: keepName }) }),
  root: defineCollection({ loader: glob({ pattern: ["about.md"], base: "..", generateId: keepName }) }),
};
