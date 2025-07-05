"""
seofrog/parsers/seo_parser.py
SEO Parser Modular v0.2 - ORQUESTRADOR DOS PARSERS ESPECIALIZADOS
🚀 VERSÃO CORRIGIDA: Apenas orquestra os parsers especializados
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Any
from datetime import datetime

from seofrog.utils.logger import get_logger
from seofrog.core.exceptions import ParseException

# === IMPORTS DOS PARSERS ESPECIALIZADOS ===
from seofrog.parsers.headings_parser import HeadingsParser
from seofrog.parsers.images_parser import ImagesParser
from seofrog.parsers.security_parser import SecurityParser
from seofrog.parsers.technical_parser import TechnicalParser
from seofrog.parsers.meta_parser import MetaParser
from seofrog.parsers.content_parser import ContentParser
from seofrog.parsers.links_parser import LinksParser

class SEOParser:
    """
    🎼 Parser Orquestrador - Coordena todos os parsers especializados
    Não contém lógica de parsing, apenas delega para os parsers especializados
    """

    def __init__(self):
        self.logger = get_logger('SEOParser')

        # Inicializa todos os parsers especializados
        self.meta_parser = MetaParser()
        self.headings_parser = HeadingsParser()
        self.images_parser = ImagesParser()
        self.security_parser = SecurityParser()
        self.technical_parser = TechnicalParser()
        self.content_parser = ContentParser()
        self.links_parser = LinksParser()

        self.logger.info("🎼 SEOParser modular inicializado com todos os parsers especializados")

    def parse_page(self, url: str, response: requests.Response) -> Dict[str, Any]:
        """
        🚀 Parse completo usando APENAS parsers especializados

        Args:
            url: URL da página
            response: Response object do requests

        Returns:
            Dict com todos os dados SEO extraídos pelos parsers especializados
        """

        # === DADOS BÁSICOS DA RESPOSTA ===
        data = {
            'url': url,
            'status_code': response.status_code,
            'content_type': response.headers.get('content-type', ''),
            'content_length': len(response.content),
            'response_time': response.elapsed.total_seconds(),
            'final_url': response.url,
            'crawl_timestamp': datetime.now().isoformat()
        }

        # Se não é HTML, retorna apenas dados básicos
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type:
            data['content_type_category'] = self._categorize_content_type(content_type)
            return data

        try:
            soup = BeautifulSoup(response.content, 'lxml')

            # 1. CONTENT PARSER
            try:
                content_data = self.content_parser.parse(soup)
                data.update(content_data)
                self.logger.debug(f"✅ ContentParser: {len(content_data)} campos")
            except Exception as e:
                self.logger.error(f"❌ ContentParser falhou: {e}")
                data['content_parser_error'] = str(e)

            # 2. META PARSER
            try:
                meta_data = self.meta_parser.parse(soup, url)
                data.update(meta_data)
                self.logger.debug(f"✅ MetaParser: {len(meta_data)} campos")
            except Exception as e:
                self.logger.error(f"❌ MetaParser falhou: {e}")
                data['meta_parser_error'] = str(e)

            # 3. HEADINGS PARSER
            try:
                word_count = data.get('word_count')
                headings_data = self.headings_parser.parse(soup, word_count)
                data.update(headings_data)
                self.logger.debug(f"✅ HeadingsParser: {len(headings_data)} campos")
            except Exception as e:
                self.logger.error(f"❌ HeadingsParser falhou: {e}")
                data['headings_parser_error'] = str(e)

            # 4. IMAGES PARSER
            try:
                word_count = data.get('word_count')
                images_data = self.images_parser.parse(soup, word_count)
                data.update(images_data)
                self.logger.debug(f"✅ ImagesParser: {len(images_data)} campos")
            except Exception as e:
                self.logger.error(f"❌ ImagesParser falhou: {e}")
                data['images_parser_error'] = str(e)

            # 5. SECURITY PARSER
            try:
                security_data = self.security_parser.parse(soup, url, response.headers)
                data.update(security_data)
                self.logger.debug(f"✅ SecurityParser: {len(security_data)} campos")
            except Exception as e:
                self.logger.error(f"❌ SecurityParser falhou: {e}")
                data['security_parser_error'] = str(e)

            # 6. TECHNICAL PARSER
            try:
                technical_data = self.technical_parser.parse(soup, url)
                data.update(technical_data)
                self.logger.debug(f"✅ TechnicalParser: {len(technical_data)} campos")
            except Exception as e:
                self.logger.error(f"❌ TechnicalParser falhou: {e}")
                data['technical_parser_error'] = str(e)

            # 7. LINKS PARSER
            try:
                word_count = data.get('word_count')
                links_data = self.links_parser.parse(soup, url, word_count)
                data.update(links_data)
                self.logger.debug(f"✅ LinksParser: {len(links_data)} campos")

                # ⬇️ Adiciona detalhes de redirects internos para exportação
                data['internal_redirects_details'] = self.links_parser.internal_redirect_links

            except Exception as e:
                self.logger.error(f"❌ LinksParser falhou: {e}")
                data['links_parser_error'] = str(e)

            total_fields = len(data)
            errors = len([k for k in data.keys() if k.endswith('_parser_error')])

            self.logger.info(f"🌟 Parsing completo: {total_fields} campos extraídos")
            if errors > 0:
                self.logger.warning(f"⚠️ {errors} parsers com erro")

            return data

        except Exception as e:
            self.logger.error(f"❌ Erro crítico no parsing de {url}: {e}")
            data['parse_error'] = str(e)
            return data

    def _categorize_content_type(self, content_type: str) -> str:
        if 'image/' in content_type:
            return 'image'
        elif 'text/css' in content_type:
            return 'css'
        elif 'javascript' in content_type or 'text/js' in content_type:
            return 'javascript'
        elif 'application/pdf' in content_type:
            return 'pdf'
        elif 'application/json' in content_type:
            return 'json'
        elif 'text/xml' in content_type or 'application/xml' in content_type:
            return 'xml'
        else:
            return 'other'

    def get_parser_status(self) -> Dict[str, bool]:
        return {
            'meta_parser': self.meta_parser is not None,
            'headings_parser': self.headings_parser is not None,
            'images_parser': self.images_parser is not None,
            'security_parser': self.security_parser is not None,
            'technical_parser': self.technical_parser is not None,
            'content_parser': self.content_parser is not None,
            'links_parser': self.links_parser is not None,
        }

    def get_parser_info(self) -> Dict[str, str]:
        return {
            'architecture': 'modular',
            'version': '0.2',
            'total_parsers': 7,
            'parsers': [
                'MetaParser - title, description, canonical, robots',
                'HeadingsParser - H1-H6 com análise avançada',
                'ImagesParser - alt text, src, dimensões, lazy loading',
                'SecurityParser - Mixed Content, Security Headers, Vulnerabilidades',
                'TechnicalParser - viewport, charset, favicon, DOCTYPE, performance',
                'ContentParser - word count, character count, text ratio',
                'LinksParser - links internos/externos, anchor text, redirects'
            ]
        }
