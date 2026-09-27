"""Web browsing and scraping tools."""
import urllib.request
import urllib.error
from html.parser import HTMLParser
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from tools.base import Tool


class SimpleHTMLToTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.ignore_tags = {'script', 'style', 'head', 'meta', 'link', 'noscript', 'svg', 'path'}
        self.current_tag = []

    def handle_starttag(self, tag, attrs):
        self.current_tag.append(tag)

    def handle_endtag(self, tag):
        if self.current_tag and self.current_tag[-1] == tag:
            self.current_tag.pop()
        # Add newlines for block elements
        if tag in {'p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr'}:
            self.text.append('\n')

    def handle_data(self, data):
        if not self.current_tag or self.current_tag[-1] not in self.ignore_tags:
            text = data.strip()
            if text:
                self.text.append(text + ' ')


def _html_to_text(html: str) -> str:
    parser = SimpleHTMLToTextParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        pass
    
    # Clean up excess newlines
    lines = "".join(parser.text).split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    return "\n".join(cleaned_lines)


class FetchWebpageSchema(BaseModel):
    url: str = Field(..., description="The full HTTP/HTTPS URL to fetch.")

class FetchWebpage(Tool):
    def __init__(self):
        super().__init__(
            name="fetch_webpage",
            description=(
                "Fetch a URL from the internet and return its textual content. "
                "Use this to read documentation, APIs, or articles. Extracts visible text from HTML."
            ),
            input_schema=FetchWebpageSchema,
            requires_permission=False,
        )

    def execute(self, url: str, **kwargs) -> str:
        if not url.startswith("http"):
            url = "https://" + url
            
        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ChattyChronos/3.0',
                    'Accept-Encoding': 'gzip, deflate',
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                content_type = response.headers.get_content_type()
                charset = response.headers.get_content_charset() or 'utf-8'

                raw_data = response.read()

                # Decompress if the server sent gzip/deflate (common on modern sites
                # like python.org). urllib does NOT do this automatically.
                encoding = (response.headers.get('Content-Encoding') or '').lower()
                try:
                    if 'gzip' in encoding:
                        import gzip
                        raw_data = gzip.decompress(raw_data)
                    elif 'deflate' in encoding:
                        import zlib
                        try:
                            raw_data = zlib.decompress(raw_data)
                        except zlib.error:
                            raw_data = zlib.decompress(raw_data, -zlib.MAX_WBITS)
                except Exception:
                    pass  # if decompression fails, fall through with raw bytes

                try:
                    text_data = raw_data.decode(charset)
                except (UnicodeDecodeError, LookupError):
                    text_data = raw_data.decode('utf-8', errors='replace')
                
                if 'text/html' in content_type:
                    extracted = _html_to_text(text_data)
                else:
                    # For JSON, text/plain, etc
                    extracted = text_data
                
                # Cap the length to keep the LLM context (and provider payloads)
                # reasonable. Full doc pages can be huge and cause 413 Payload Too
                # Large on cloud/gateway providers. 8000 chars is plenty of signal.
                max_len = 8000
                if len(extracted) > max_len:
                    extracted = extracted[:max_len] + f"\n\n[Truncated — original was {len(extracted)} chars]"
                    
                return extracted
                
        except urllib.error.URLError as e:
            return f"Failed to fetch {url}: {e.reason}"
        except Exception as e:
            return f"Error fetching {url}: {str(e)}"


# ─── Web Search (DuckDuckGo, no API key) ─────────────────────────────────────

class WebSearchSchema(BaseModel):
    query: str = Field(..., description="The search query — what to look up on the web.")
    max_results: int = Field(5, description="Maximum number of results to return (1-10).")


class WebSearch(Tool):
    """Search the web (DuckDuckGo HTML endpoint, no API key required).

    Returns a list of results (title, snippet, URL). Use it when you need current
    information, or information beyond your training data, then optionally call
    fetch_webpage on the most relevant URL to read it in full.
    """

    def __init__(self):
        super().__init__(
            name="web_search",
            description=(
                "Search the internet for current or unknown information. Returns a "
                "ranked list of results (title, snippet, URL). Use this when the user "
                "asks about recent events, versions, prices, or anything you are unsure "
                "of or that may be newer than your knowledge. Follow up with "
                "fetch_webpage on a result URL to read the full page."
            ),
            input_schema=WebSearchSchema,
            requires_permission=False,
        )

    def execute(self, query: str, max_results: int = 5, **kwargs) -> str:
        import urllib.parse
        import urllib.request
        import re
        from html import unescape

        max_results = max(1, min(int(max_results or 5), 10))
        # DuckDuckGo HTML endpoint (no API key). POST is more reliable than GET here.
        url = "https://html.duckduckgo.com/html/"
        data = urllib.parse.urlencode({"q": query}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ChattyChronos/3.0",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            return f"Web search failed for '{query}': {e}"

        # Parse result blocks. DuckDuckGo HTML uses result__a for links and
        # result__snippet for snippets.
        results = []
        # Links: <a ... class="result__a" href="...">Title</a>
        link_pattern = re.compile(
            r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE,
        )
        snippet_pattern = re.compile(
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE,
        )

        def _clean(raw: str) -> str:
            text = re.sub(r"<[^>]+>", "", raw)  # strip tags
            return unescape(text).strip()

        def _resolve(href: str) -> str:
            # DuckDuckGo wraps links like /l/?uddg=<encoded-url>
            if href.startswith("//duckduckgo.com/l/") or "uddg=" in href:
                m = re.search(r"uddg=([^&]+)", href)
                if m:
                    return urllib.parse.unquote(m.group(1))
            if href.startswith("//"):
                return "https:" + href
            return href

        links = link_pattern.findall(html)
        snippets = snippet_pattern.findall(html)

        for i, (href, title) in enumerate(links[:max_results]):
            snippet = _clean(snippets[i]) if i < len(snippets) else ""
            results.append({
                "title": _clean(title),
                "url": _resolve(href),
                "snippet": snippet,
            })

        if not results:
            return (
                f"No web results found for '{query}'. The search page format may have "
                f"changed, or the query returned nothing. Consider asking the user for a source."
            )

        lines = [f"Web search results for '{query}':\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}")
            if r["snippet"]:
                lines.append(f"   {r['snippet']}")
            lines.append(f"   {r['url']}\n")
        return "\n".join(lines)
