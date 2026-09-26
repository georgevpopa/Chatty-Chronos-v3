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
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ChattyChronos/1.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                content_type = response.headers.get_content_type()
                charset = response.headers.get_content_charset() or 'utf-8'
                
                raw_data = response.read()
                try:
                    text_data = raw_data.decode(charset)
                except UnicodeDecodeError:
                    text_data = raw_data.decode('utf-8', errors='replace')
                
                if 'text/html' in content_type:
                    extracted = _html_to_text(text_data)
                else:
                    # For JSON, text/plain, etc
                    extracted = text_data
                
                # Cap the length to prevent blowing up the LLM context
                max_len = 30000
                if len(extracted) > max_len:
                    extracted = extracted[:max_len] + f"\n\n[Truncated — original was {len(extracted)} chars]"
                    
                return extracted
                
        except urllib.error.URLError as e:
            return f"Failed to fetch {url}: {e.reason}"
        except Exception as e:
            return f"Error fetching {url}: {str(e)}"
