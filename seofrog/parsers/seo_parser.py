"""
seofrog/parsers/seo_parser.py
High level parser that aggregates all modular parsers.
"""

from typing import Any, Dict, Union
from bs4 import BeautifulSoup

from .meta_parser import MetaParser
from .technical_parser import TechnicalParser
from .social_parser import SocialParser
from .schema_parser import SchemaParser
from .links_parser import LinksParser
from seofrog.utils.logger import get_logger


class SEOParser:
    """Aggregate parser that runs all individual parsers for a page."""

    def __init__(self) -> None:
        self.logger = get_logger("SEOParser")
        self.meta_parser = MetaParser()
        self.technical_parser = TechnicalParser()
        self.social_parser = SocialParser()
        self.schema_parser = SchemaParser()
        self.links_parser = LinksParser()

    # ------------------------------------------------------------------
    def parse_url_data(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Parse a BeautifulSoup object and return SEO information."""
        data: Dict[str, Any] = {"url": url}

        try:
            data.update(self.meta_parser.parse(soup, url))
            data.update(self.technical_parser.parse(soup, url))
            data.update(self.social_parser.parse(soup, url))
            data.update(self.schema_parser.parse(soup, url))

            word_count = data.get("word_count")
            links_data = self.links_parser.parse(soup, url, word_count)
            data.update(links_data)
            self.logger.debug(f"✅ LinksParser: {len(links_data)} campos")

            redirects_for_this_url = self.links_parser.get_redirects_for_url(url)
            if redirects_for_this_url:
                legacy_format = []
                for redirect in redirects_for_this_url:
                    legacy_format.append(
                        {
                            "From": redirect.get("from_url", ""),
                            "To (Original)": redirect.get("to_original", ""),
                            "To (Final)": redirect.get("to_final", ""),
                            "Anchor": redirect.get("anchor_text", ""),
                            "Alt Text": redirect.get("alt_text", ""),
                            "Follow": "True" if redirect.get("follow", True) else "False",
                            "Target": redirect.get("target", ""),
                            "Rel": redirect.get("rel", ""),
                            "Código": redirect.get("status_code", ""),
                            "Criticidade": redirect.get("criticidade", ""),
                            "Sugestão": redirect.get("sugestao", ""),
                            "Link Path": redirect.get("link_path", ""),
                        }
                    )
                data["internal_redirects_details"] = legacy_format
                self.logger.debug(
                    f"✅ {len(legacy_format)} redirects específicos para {url}"
                )
            else:
                data["internal_redirects_details"] = []

            total_redirects = self.links_parser.get_total_redirects_count()
            data["total_redirects_found"] = total_redirects

            total_fields = len(data)
            errors = len([k for k in data.keys() if k.endswith("_parser_error")])
            redirects_count = len(data.get("internal_redirects_details", []))

            self.logger.info(
                f"🌟 Parsing completo: {total_fields} campos, {redirects_count} redirects"
            )
            if errors > 0:
                self.logger.warning(f"⚠️ {errors} parsers com erro")

            return data
        except Exception as e:  # pragma: no cover - unexpected issues
            self.logger.error(f"❌ Erro crítico no parsing de {url}: {e}")
            data["parse_error"] = str(e)
            data["internal_redirects_details"] = []
            return data

    # ------------------------------------------------------------------
    def parse_page(self, url: str, response: Any) -> Dict[str, Any]:
        """Convenience helper to parse a ``requests.Response`` object."""
        soup = BeautifulSoup(response.content, "lxml")
        return self.parse_url_data(soup, url)

    def finalize_parsing(self) -> None:
        """Emit a summary after parsing many pages."""
        if hasattr(self.links_parser, "log_final_summary"):
            self.links_parser.log_final_summary()
        if hasattr(self.links_parser, "log_cache_summary"):
            self.links_parser.log_cache_summary()

