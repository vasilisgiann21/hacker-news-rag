import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit, urlunsplit, urlparse
import aiofiles
import json
import random
from playwright.async_api import async_playwright
from readability import Document
from urllib.robotparser import RobotFileParser
from datetime import datetime

# ---------------------------
# Global: User Agents & Header Generator
# ---------------------------
user_agents = {
    "win10_chrome_123": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "win11_chrome_122": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "win10_firefox_124": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "win10_edge_123": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.2420.81",
    "win10_opera_108": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0",
    "mac_chrome_123": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "mac_safari_17_4": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "mac_firefox_124": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
    "mac_edge_123": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.2420.81",
    "linux_chrome_123": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "linux_firefox_124": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "linux_firefox_esr": "Mozilla/5.0 (X11; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0",
    "android_14_chrome": "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.40 Mobile Safari/537.36",
    "android_13_samsung": "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 Chrome/116.0.0.0 Mobile Safari/537.36",
    "android_12_firefox": "Mozilla/5.0 (Android 12; Mobile; rv:124.0) Gecko/124.0 Firefox/124.0",
    "ios_17_safari": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "ios_16_safari": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "ios_17_chrome": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/123.0.6312.52 Mobile/15E148 Safari/604.1",
    "googlebot_desktop": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "googlebot_mobile": "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.80 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "bingbot": "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"
}

def get_random_header():
    random_ua = random.choice(list(user_agents.values()))
    return {
        "User-Agent": random_ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

robots_cache = {}

async def can_fetch(url, session, user_agent="*"):
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = base + "/robots.txt"

    if base not in robots_cache:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            async with session.get(robots_url, timeout=10) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    rp.parse(content.splitlines())
                else:
                    rp = None
        except Exception:
            rp = None
        robots_cache[base] = rp

    rp = robots_cache[base]
    if rp is None:
        return True
    return rp.can_fetch(user_agent, url)

def should_follow(url: str, base_domain: str, allowed_path_prefix: str = None) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.netloc != base_domain:
        return False
    if allowed_path_prefix and not parsed.path.startswith(allowed_path_prefix):
        return False
    return True

def normalize_url(url: str) -> str:
    """Normalize URL: lowercase scheme/netloc, remove trailing slash, KEEP query string."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip('/')
    if not path:
        path = '/'
    query = parsed.query
    fragment = parsed.fragment
    normalized = f"{scheme}://{netloc}{path}"
    if query:
        normalized += f"?{query}"
    if fragment:
        normalized += f"#{fragment}"
    return normalized

# ---------------------------
# Core Functions
# ---------------------------
async def disk_writer(writer_queue, filename):
    async with aiofiles.open(filename, mode='a', encoding="utf-8") as f:
        while True:
            content = await writer_queue.get()
            try:
                new_content = json.dumps(content, ensure_ascii=False) + "\n"
                await f.write(new_content)
            except Exception as e:
                print(f"Scribe Error: {e}")
            finally:
                writer_queue.task_done()

async def fetch_with_retry(session, url, headers, max_retries=3):
    """Fetch with retry and exponential backoff. Returns (status_code, html) or (None, None)."""
    for attempt in range(max_retries):
        try:
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status in (429, 503, 502, 504):
                    wait = 2 ** attempt
                    print(f"[Retry] {response.status} on {url}, waiting {wait}s")
                    await asyncio.sleep(wait)
                    continue
                html = await response.text()
                return response.status, html
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt == max_retries - 1:
                return None, None
            wait = 2 ** attempt
            print(f"[Retry] Error {e} on {url}, waiting {wait}s")
            await asyncio.sleep(wait)
    return None, None

def extract_intel(html, url, base_domain, allowed_path_prefix=None):
    doc = Document(html)
    clean_html = doc.summary()
    clean_text = BeautifulSoup(clean_html, "html.parser").get_text(separator="\n", strip=True)
    title = doc.title()

    if not clean_text:
        soup = BeautifulSoup(html, "html.parser")
        for selector in ["article", "main", ".content", "#content", ".post-body"]:
            container = soup.select_one(selector)
            if container:
                clean_text = container.get_text(separator="\n", strip=True)
                break
        if not clean_text:
            clean_text = soup.get_text(separator="\n", strip=True)

    code_blocks = []
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["pre", "code"]):
        code_text = tag.get_text().strip()
        if code_text and len(code_text) > 10:
            code_blocks.append(code_text)
    for div in soup.find_all("div", class_=["code", "codeblock", "exploit-code"]):
        code_text = div.get_text().strip()
        if code_text:
            code_blocks.append(code_text)

    links = []
    for a_tag in soup.find_all('a'):
        href = a_tag.get("href")
        if href:
            new_link = urljoin(url, href)
            parsed = urlsplit(new_link)
            clean_link = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
            if should_follow(clean_link, base_domain, allowed_path_prefix):
                links.append(clean_link)

    return {
        "url": url,
        "title": title,
        "content": clean_text,
        "code_snippets": code_blocks,
        "links": links
    }

async def fetch_with_playwright(url, browser):
    """Render JavaScript page using shared browser instance."""
    page = await browser.new_page()
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        html = await page.content()
        return html
    except Exception as e:
        print(f"[Playwright] Error on {url}: {e}")
        return ""
    finally:
        await page.close()

async def fetch_data(max_depth, max_pages, url_queue, writer_queue, session, visited,
                    base_domain, allowed_path_prefix, browser=None):
    while True:
        url, current_depth = await url_queue.get()
        headers = get_random_header()

        await asyncio.sleep(1)  # Polite delay

        status, html = await fetch_with_retry(session, url, headers)
        if status is None:
            print(f"[!] Failed after retries: {url}")
            url_queue.task_done()
            continue

        try:
            if status == 200:
                result_dict = await asyncio.to_thread(extract_intel, html, url, base_domain, allowed_path_prefix)

                if not result_dict.get("content") and not result_dict.get("code_snippets") and browser:
                    print(f"[~] Possible JS page, trying Playwright: {url}")
                    html_rendered = await fetch_with_playwright(url, browser)
                    if html_rendered:
                        result_dict = await asyncio.to_thread(extract_intel, html_rendered, url, base_domain, allowed_path_prefix)

                if result_dict.get("content") or result_dict.get("code_snippets"):
                    print(f"[+] Payload Exfiltrated: {url}")
                    await writer_queue.put({
                        "url": result_dict["url"],
                        "title": result_dict.get("title", ""),
                        "content": result_dict.get("content", ""),
                        "code_snippets": result_dict.get("code_snippets", []),
                        "depth": current_depth,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                else:
                    print(f"[-] Scanned (No Payload): {url}")

                if len(visited) < max_pages and current_depth < max_depth:
                    for new_link in result_dict.get("links", []):
                        new_link = normalize_url(new_link)
                        if new_link not in visited:
                            new_depth = current_depth + 1
                            if new_depth <= max_depth:
                                if await can_fetch(new_link, session, headers.get("User-Agent", "*")):
                                    visited.add(new_link)
                                    await url_queue.put((new_link, new_depth))
                                else:
                                    print(f"[Robots] Disallowed: {new_link}")
            else:
                print(f"[!] Access Denied (HTTP {status}): {url}")
        except Exception as e:
            print(f"[x] Connection dropped on {url} - {e}")
        finally:
            url_queue.task_done()

async def main():
    base = "https://httpbin.org/headers"  # Replace with your target
    parsed_base = urlparse(base)
    base_domain = parsed_base.netloc
    allowed_path_prefix = parsed_base.path.rstrip('/')

    writer_queue = asyncio.Queue()
    url_queue = asyncio.Queue()
    visited = set()
    visited.add(base)

    max_depth = 100
    max_pages = 10000
    num_workers = 10

    connector = aiohttp.TCPConnector(
        limit=20,
        limit_per_host=5,
        force_close=False,
        enable_cleanup_closed=True
    )

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)

    tasks = []
    async with aiohttp.ClientSession(connector=connector) as session:
        await url_queue.put((base, 0))

        scribe_task = asyncio.create_task(disk_writer(writer_queue, "output.jsonl"))

        for i in range(num_workers):
            task = asyncio.create_task(fetch_data(
                max_depth, max_pages, url_queue, writer_queue, session, visited,
                base_domain, allowed_path_prefix, browser
            ))
            tasks.append(task)
            await asyncio.sleep(0.5)

        await url_queue.join()
        await writer_queue.join()

        for task in tasks:
            task.cancel()
        scribe_task.cancel()
        await asyncio.gather(*tasks, scribe_task, return_exceptions=True)

    await browser.close()
    await playwright.stop()
    print("Crawl finished.")

if __name__ == "__main__":
    asyncio.run(main())
