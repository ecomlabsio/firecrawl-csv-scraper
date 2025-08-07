#!/usr/bin/env python3
"""
Crawl hardrace.co.uk for product detail URLs and export a CSV.

Detection heuristics (any one is enough):
- JSON-LD with "@type": "Product"
- <meta property="og:type" content="product">
- presence of Product schema in LD+JSON, even minified

Respects robots.txt, stays on-domain, follows pagination & category links.
"""

import argparse, csv, re, time, sys, urllib.parse as up
from collections import deque
from typing import Set, Tuple

import requests
from bs4 import BeautifulSoup
import tldextract
import urllib.robotparser as robotparser

DEFAULT_UA = "Mozilla/5.0 (compatible; url-exporter/1.0; +https://example.local)"
PRODUCT_JSONLD_RE = re.compile(r'"@type"\s*:\s*"(?:Product|product)"', re.I)
OG_PRODUCT_RE = re.compile(r'<meta[^>]+property=["\']og:type["\'][^>]+content=["\']product["\']', re.I)

def normalize_url(url: str) -> str:
    u = up.urlsplit(url)
    scheme = u.scheme or "https"
    netloc = u.netloc.lower()
    path = u.path or "/"
    # strip trailing slash except root
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    query = ""  # drop params to avoid dupes
    frag = ""
    return up.urlunsplit((scheme, netloc, path, query, frag))

def same_site(url: str, allowed_hosts: Set[str]) -> bool:
    host = up.urlsplit(url).netloc.lower()
    return host in allowed_hosts

def get_allowed_hosts(start_url: str) -> Set[str]:
    parts = up.urlsplit(start_url)
    host = parts.netloc.lower()
    ext = tldextract.extract(host)
    root_host = ".".join([p for p in [ext.domain, ext.suffix] if p])
    variants = {host}
    # include www / non-www variants of same registered domain
    if not host.startswith("www.") and root_host:
        variants.add("www." + root_host)
        variants.add(root_host)
    return variants

def is_product_html(html: str) -> bool:
    if not html:
        return False
    if PRODUCT_JSONLD_RE.search(html):
        return True
    if OG_PRODUCT_RE.search(html):
        return True
    # quick extra check: Magento product page often has product-info-main
    if 'class="product-info-main"' in html or "product-info-main" in html:
        return True
    return False

def extract_links(soup: BeautifulSoup, base_url: str) -> Set[str]:
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        absu = up.urljoin(base_url, href)
        links.add(absu)
    return links

def get_canonical(soup: BeautifulSoup, url: str) -> str:
    link = soup.find("link", rel=lambda v: v and "canonical" in v.lower())
    if link and link.get("href"):
        try:
            return normalize_url(up.urljoin(url, link["href"]))
        except Exception:
            pass
    return normalize_url(url)

def fetch(session: requests.Session, url: str, timeout=20) -> Tuple[int, str]:
    r = session.get(url, timeout=timeout)
    ctype = r.headers.get("Content-Type", "")
    if "text/html" not in ctype and "application/xhtml" not in ctype:
        return r.status_code, ""
    return r.status_code, r.text

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="https://www.hardrace.co.uk/", help="Start URL")
    ap.add_argument("--out", default="hardrace_product_urls.csv", help="Output CSV path")
    ap.add_argument("--delay", type=float, default=1.0, help="Seconds between requests")
    ap.add_argument("--max-pages", type=int, default=15000, help="Max pages to crawl")
    ap.add_argument("--ua", default=DEFAULT_UA, help="User-Agent")
    args = ap.parse_args()

    start = normalize_url(args.start)
    allowed_hosts = get_allowed_hosts(start)

    # robots.txt
    robots_url = up.urlunsplit((up.urlsplit(start).scheme, list(allowed_hosts)[0], "/robots.txt", "", ""))
    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
    except Exception:
        # proceed cautiously if robots can’t be fetched
        pass

    s = requests.Session()
    s.headers.update({"User-Agent": args.ua, "Accept": "text/html,application/xhtml+xml"})

    q = deque([start])
    seen: Set[str] = set()
    product_urls: Set[str] = set()
    pages_crawled = 0

    while q and pages_crawled < args.max_pages:
        url = q.popleft()
        if url in seen:
            continue
        seen.add(url)

        if not same_site(url, allowed_hosts):
            continue
        if rp.default_entry and not rp.can_fetch(args.ua, url):
            continue

        try:
            status, html = fetch(s, url)
        except requests.RequestException:
            continue

        pages_crawled += 1
        if status != 200 or not html:
            time.sleep(args.delay)
            continue

        soup = BeautifulSoup(html, "html.parser")

        # If it's a product page, store canonical and skip queueing further from it (optional)
        if is_product_html(html):
            canon = get_canonical(soup, url)
            if same_site(canon, allowed_hosts):
                product_urls.add(canon)

        # enqueue internal links (pagination, categories, etc.)
        for link in extract_links(soup, url):
            n = normalize_url(link)
            if same_site(n, allowed_hosts) and n not in seen:
                q.append(n)

        # be polite
        time.sleep(args.delay)

    # write CSV
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url"])
        for u in sorted(product_urls):
            w.writerow([u])

    print(f"Crawled pages: {pages_crawled}")
    print(f"Found product URLs: {len(product_urls)}")
    print(f"Wrote: {args.out}")

if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    main()
