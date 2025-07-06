import datetime
import requests

from seofrog.core.crawler import SEOFrog, URLManager
from seofrog.core.config import CrawlConfig


class DummyHTTPEngine:
    def __init__(self, response, redirect_chain=None):
        self.response = response
        self.redirect_chain = redirect_chain or []

    def fetch_url(self, url):
        return self.response, self.redirect_chain, {}


def make_response(url, html, status_code=200, final_url=None):
    resp = requests.Response()
    resp.status_code = status_code
    resp._content = html.encode("utf-8")
    resp.headers["content-type"] = "text/html"
    resp.url = final_url or url
    resp.elapsed = datetime.timedelta(seconds=0.1)
    return resp


def setup_seofrog(response, redirect_chain=None):
    config = CrawlConfig(max_urls=10, max_depth=1, respect_robots=False)
    crawler = SEOFrog(config)
    crawler.url_manager = URLManager("example.com")
    crawler.http_engine = DummyHTTPEngine(response, redirect_chain)
    return crawler


def test_internal_links_parsed():
    html = "<html><body><a href='/about'>About</a><a href='http://ext.com'>Ext</a></body></html>"
    resp = make_response("http://example.com", html)
    crawler = setup_seofrog(resp)

    result = crawler.crawl_url("http://example.com", 0)
    assert "internal_links_details" in result
    assert len(result["internal_links_details"]) == 1
    assert result["has_redirect"] is False


def test_redirect_info_populated():
    html = "<html><body><a href='/next'>Next</a></body></html>"
    resp = make_response("http://example.com", html, final_url="http://example.com/home")
    redirect_chain = [{"url": "http://example.com", "status_code": 301, "location": "/home"}]
    crawler = setup_seofrog(resp, redirect_chain)

    result = crawler.crawl_url("http://example.com", 0)
    assert result["has_redirect"] is True
    assert result["redirect_chain_length"] == 1
    assert result["redirect_status_code"] == 301
    assert result["internal_links_details"]
