"""
seofrog/parsers/regex_base.py
Base parser usando regex (sem BeautifulSoup)
"""

import re
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urlparse, urljoin
from seofrog.utils.logger import get_logger


class RegexParserMixin:
    """
    Mixin com métodos utilitários para parsing com regex
    Substituto para BeautifulSoup em parsers simples
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    # ==========================================
    # HELPERS DE BUSCA COM REGEX
    # ==========================================
    
    def find_tag_content(self, html: str, tag: str, attrs: Dict = None) -> Optional[str]:
        """
        Encontra conteúdo de uma tag usando regex
        
        Args:
            html: HTML content
            tag: Tag name (e.g., 'title', 'h1')
            attrs: Dict of attributes to match
            
        Returns:
            Content of the tag or None
        """
        try:
            if attrs:
                # Build attribute pattern
                attr_pattern = ""
                for key, value in attrs.items():
                    if isinstance(value, str):
                        attr_pattern += f'[^>]*{key}=["\']?{re.escape(value)}["\']?'
                    elif isinstance(value, dict) and 'class' in key:
                        # Handle class attributes specially
                        classes = value if isinstance(value, list) else [value]
                        class_pattern = '|'.join(re.escape(cls) for cls in classes)
                        attr_pattern += f'[^>]*class=["\']?[^"\']*({class_pattern})[^"\']*["\']?'
                
                pattern = f'<{tag}{attr_pattern}[^>]*>(.*?)</{tag}>'
            else:
                pattern = f'<{tag}[^>]*>(.*?)</{tag}>'
            
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            return match.group(1).strip() if match else None
            
        except Exception as e:
            self.logger.debug(f"Error finding tag {tag}: {e}")
            return None
    
    def find_all_tags(self, html: str, tag: str, attrs: Dict = None) -> List[str]:
        """
        Encontra todos os conteúdos de uma tag
        
        Args:
            html: HTML content
            tag: Tag name
            attrs: Dict of attributes to match
            
        Returns:
            List of tag contents
        """
        try:
            if attrs:
                attr_pattern = ""
                for key, value in attrs.items():
                    attr_pattern += f'[^>]*{key}=["\']?{re.escape(str(value))}["\']?'
                pattern = f'<{tag}{attr_pattern}[^>]*>(.*?)</{tag}>'
            else:
                pattern = f'<{tag}[^>]*>(.*?)</{tag}>'
            
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            return [match.strip() for match in matches]
            
        except Exception as e:
            self.logger.debug(f"Error finding all tags {tag}: {e}")
            return []
    
    def find_meta_content(self, html: str, name: str = None, property: str = None) -> Optional[str]:
        """
        Encontra conteúdo de meta tag
        
        Args:
            html: HTML content
            name: Meta name attribute
            property: Meta property attribute (for og:, twitter:, etc.)
            
        Returns:
            Content attribute value
        """
        try:
            if name:
                pattern = rf'<meta[^>]*name=["\']?{re.escape(name)}["\']?[^>]*content=["\']([^"\']*)["\']'
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
                    
                # Try alternative order
                pattern = rf'<meta[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']?{re.escape(name)}["\']?'
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
            
            if property:
                pattern = rf'<meta[^>]*property=["\']?{re.escape(property)}["\']?[^>]*content=["\']([^"\']*)["\']'
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
                    
                # Try alternative order
                pattern = rf'<meta[^>]*content=["\']([^"\']*)["\'][^>]*property=["\']?{re.escape(property)}["\']?'
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error finding meta content: {e}")
            return None
    
    def find_links(self, html: str, base_url: str = None) -> List[Dict[str, str]]:
        """
        Encontra todos os links na página
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of link dictionaries with 'href', 'text', 'title'
        """
        try:
            links = []
            # Pattern to match <a> tags with href
            pattern = r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>'
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            
            for href, text in matches:
                href = href.strip()
                text = re.sub(r'<[^>]+>', '', text).strip()  # Remove HTML tags from text
                
                # Resolve relative URLs
                if base_url and href and not href.startswith(('http://', 'https://', 'mailto:', 'tel:')):
                    if href.startswith('/'):
                        parsed_base = urlparse(base_url)
                        href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
                    else:
                        href = urljoin(base_url, href)
                
                links.append({
                    'href': href,
                    'text': text,
                    'title': ''  # Could extract title attribute if needed
                })
            
            return links
            
        except Exception as e:
            self.logger.debug(f"Error finding links: {e}")
            return []
    
    def find_images(self, html: str, base_url: str = None) -> List[Dict[str, str]]:
        """
        Encontra todas as imagens na página
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs
            
        Returns:
            List of image dictionaries with 'src', 'alt', 'title'
        """
        try:
            images = []
            # Pattern to match <img> tags
            pattern = r'<img[^>]*src=["\']([^"\']*)["\'][^>]*(?:alt=["\']([^"\']*)["\'])?[^>]*>'
            matches = re.findall(pattern, html, re.IGNORECASE)
            
            for match in matches:
                src = match[0].strip() if match[0] else ""
                alt = match[1].strip() if len(match) > 1 and match[1] else ""
                
                # Resolve relative URLs
                if base_url and src and not src.startswith(('http://', 'https://', 'data:')):
                    if src.startswith('/'):
                        parsed_base = urlparse(base_url)
                        src = f"{parsed_base.scheme}://{parsed_base.netloc}{src}"
                    else:
                        src = urljoin(base_url, src)
                
                images.append({
                    'src': src,
                    'alt': alt,
                    'title': ''  # Could extract title attribute if needed
                })
            
            return images
            
        except Exception as e:
            self.logger.debug(f"Error finding images: {e}")
            return []
    
    def count_tags(self, html: str, tag: str) -> int:
        """
        Conta ocorrências de uma tag
        
        Args:
            html: HTML content
            tag: Tag name to count
            
        Returns:
            Number of occurrences
        """
        try:
            pattern = f'<{tag}[^>]*>'
            matches = re.findall(pattern, html, re.IGNORECASE)
            return len(matches)
        except Exception as e:
            self.logger.debug(f"Error counting tags {tag}: {e}")
            return 0
    
    def clean_text(self, text: str) -> str:
        """
        Remove HTML tags and clean text
        
        Args:
            text: Text with possible HTML
            
        Returns:
            Clean text
        """
        if not text:
            return ""
        
        try:
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', text)
            # Remove extra whitespace
            text = ' '.join(text.split())
            return text.strip()
        except Exception as e:
            self.logger.debug(f"Error cleaning text: {e}")
            return text
    
    def extract_text_content(self, html: str) -> str:
        """
        Extrai todo o texto visível da página
        
        Args:
            html: HTML content
            
        Returns:
            Plain text content
        """
        try:
            # Remove script and style elements
            html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.IGNORECASE | re.DOTALL)
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', html)
            # Clean up whitespace
            text = ' '.join(text.split())
            return text.strip()
        except Exception as e:
            self.logger.debug(f"Error extracting text content: {e}")
            return ""
    
    # ==========================================
    # HELPERS DE VALIDAÇÃO
    # ==========================================
    
    def is_valid_url(self, url: str) -> bool:
        """Valida se uma URL é válida"""
        if not url or not isinstance(url, str):
            return False
        
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def normalize_url(self, url: str, base_url: str = None) -> str:
        """Normaliza uma URL"""
        if not url:
            return ""
        
        try:
            if base_url and not url.startswith(('http://', 'https://')):
                url = urljoin(base_url, url)
            return url.strip()
        except Exception:
            return url