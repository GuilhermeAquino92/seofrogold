import pytest

bs4 = pytest.importorskip("bs4")
BeautifulSoup = bs4.BeautifulSoup

from seofrog.parsers.seo_parser import SEOParser


def test_seo_parser_basic_parse():
    html = "<html><head><title>Title</title></head><body><a href='/next'>Next</a></body></html>"
    soup = BeautifulSoup(html, "lxml")
    parser = SEOParser()
    result = parser.parse_url_data(soup, "http://example.com")

    assert result["url"] == "http://example.com"
    # LinksParser should have added link details without crashing
    assert "internal_links_details" in result
    assert isinstance(result["internal_redirects_details"], list)

