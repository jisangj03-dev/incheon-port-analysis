"""새 원천의 이용 조건 원문 대조(출처 대장 선커밋의 [미확인] 닫기) — 공개 화면만 읽고 관련 문장을 옮긴다. 판정은 사람이 읽고 대장에 적는다.
결과: data/collected/v3/terms_check.json
"""
import datetime, html, re, sys
from common import get, write, say

PAGES = {
    "imf-portwatch": ["https://www.imf.org/external/terms.htm", "https://portwatch.imf.org/pages/data-and-methodology", "https://portwatch.imf.org/pages/faqs"],
    "wb-ship-density": ["https://datacatalogapi.worldbank.org/ddhxext/DatasetView?dataset_unique_id=0037580", "https://datacatalog.worldbank.org/search/dataset/0037580"],
    "copernicus-s2": ["https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice", "https://registry.opendata.aws/sentinel-2-l2a-cogs/"],
    "kobc-kcci": ["https://www.kobc.or.kr/ebz/shippinginfo/kcci/gridList.do", "https://www.kobc.or.kr/ebz/shippinginfo/kcci/view.do"],
    "osm": ["https://www.openstreetmap.org/copyright"],
}
WORDS = r"(licen[cs]e|terms|copyright|attribution|commercial|reproduc|Creative Commons|CC BY|비상업|저작권|이용|출처|재배포|무단)"


def text(h):
    h = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", h or "", flags=re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def main():
    out = {"checked": datetime.date.today().isoformat(), "pages": {}}
    for sid, urls in PAGES.items():
        recs = []
        for u in urls:
            st, h = get(u, timeout=60)
            t = text(h) if not (h or "").lstrip().startswith("{") else h
            hits = [t[max(0, m.start() - 160): m.end() + 220] for m in re.finditer(WORDS, t, re.I)][:12]
            recs.append({"url": u, "status": st, "chars": len(t), "excerpts": hits})
        out["pages"][sid] = recs
        say(sid, [(r["status"], r["chars"], len(r["excerpts"])) for r in recs])
    write("data/collected/v3/terms_check.json", out)


if __name__ == "__main__":
    sys.exit(main())
