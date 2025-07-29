"""
seofrog/parsers/meta_parser.py
Parser modular para elementos meta: title, description, keywords, canonical, robots
Refatorado para usar ParserMixin com helpers seguros
"""

from typing import Dict, Any
from bs4 import BeautifulSoup
from .base import ParserMixin, SEO_LIMITS, BRAND_SEPARATORS

class MetaParser(ParserMixin):
    """
    Parser especializado para todos os elementos meta da página
    Responsável por: title, meta description, keywords, canonical, robots
    """
    
    def __init__(self):
        super().__init__()  # Inicializa ParserMixin
    
    def parse(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Parse completo de todos os elementos meta
        
        Args:
            soup: BeautifulSoup object da página
            url: URL original da página (para comparar canonical)
            
        Returns:
            Dict com todos os dados meta extraídos
        """
        data = {}
        
        try:
            # Title tag
            self._parse_title(soup, data)
            
            # Meta description
            self._parse_meta_description(soup, data)
            
            # Meta keywords (ainda usado por alguns sites)
            self._parse_meta_keywords(soup, data)
            
            # Canonical URL
            self._parse_canonical(soup, data, url)
            
            # Meta robots directives
            self._parse_meta_robots(soup, data)
            
            # Log estatísticas usando helper do ParserMixin
            errors = 1 if 'meta_parse_error' in data else 0
            self.log_parsing_stats('MetaParser', len(data), errors)
            
        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            self.logger.error(f"Erro no parse de meta elements: {error_msg}")
            data['meta_parse_error'] = str(e).encode('utf-8', errors='replace').decode('utf-8')
            self.log_parsing_stats('MetaParser', len(data), 1)
        
        return data
    
    def _parse_title(self, soup: BeautifulSoup, data: Dict):
        """
        Parse do title tag com análise de qualidade usando helpers seguros
        """
        title_tag = self.safe_find(soup, 'title')
        
        if title_tag:
            title_text = self.extract_text_safe(title_tag)
            
            # Análise de comprimento usando helper
            title_analysis = self.analyze_text_length(
                title_text, 
                SEO_LIMITS['title']['min'], 
                SEO_LIMITS['title']['max']
            )
            
            # Dados básicos
            data['title'] = title_text
            data['title_length'] = title_analysis['length']
            data['title_words'] = title_analysis['word_count']
            
            # Análise de qualidade
            data['title_has_brand'] = self.detect_brand_pattern(title_text, BRAND_SEPARATORS)
            
            # Validações SEO (usando análise do helper)
            data['title_is_empty'] = title_analysis['is_empty']
            data['title_too_long'] = title_analysis['too_long']
            data['title_too_short'] = title_analysis['too_short']
            data['title_optimal_length'] = title_analysis['optimal']
            
        else:
            # Sem title tag
            data['title'] = ''
            data['title_length'] = 0
            data['title_words'] = 0
            data['title_has_brand'] = False
            data['title_is_empty'] = True
            data['title_too_long'] = False
            data['title_too_short'] = False
            data['title_optimal_length'] = False
    
    def _parse_meta_description(self, soup: BeautifulSoup, data: Dict):
        """
        Parse da meta description com validações SEO usando helpers seguros
        """
        meta_desc = self.find_meta_by_name(soup, 'description')
        
        if meta_desc:
            desc_text = self.extract_meta_content(meta_desc)
            
            # Análise de comprimento usando helper
            desc_analysis = self.analyze_text_length(
                desc_text,
                SEO_LIMITS['meta_description']['min'],
                SEO_LIMITS['meta_description']['max']
            )
            
            # Dados básicos
            data['meta_description'] = desc_text
            data['meta_description_length'] = desc_analysis['length']
            
            # Validações SEO (usando análise do helper)
            data['meta_description_is_empty'] = desc_analysis['is_empty']
            data['meta_description_too_long'] = desc_analysis['too_long']
            data['meta_description_too_short'] = desc_analysis['too_short']
            data['meta_description_optimal_length'] = desc_analysis['optimal']
            
        else:
            # Sem meta description
            data['meta_description'] = ''
            data['meta_description_length'] = 0
            data['meta_description_is_empty'] = True
            data['meta_description_too_long'] = False
            data['meta_description_too_short'] = False
            data['meta_description_optimal_length'] = False
    
    def _parse_meta_keywords(self, soup: BeautifulSoup, data: Dict):
        """
        Parse das meta keywords usando helpers seguros (legado, mas ainda usado)
        """
        meta_keywords = self.find_meta_by_name(soup, 'keywords')
        
        if meta_keywords:
            keywords_text = self.extract_meta_content(meta_keywords)
            data['meta_keywords'] = keywords_text
            
            # Conta keywords separadas por vírgula
            if keywords_text:
                keywords_list = [k.strip() for k in keywords_text.split(',') if k.strip()]
                data['meta_keywords_count'] = len(keywords_list)
            else:
                data['meta_keywords_count'] = 0
        else:
            data['meta_keywords'] = ''
            data['meta_keywords_count'] = 0
    
    def _parse_canonical(self, soup: BeautifulSoup, data: Dict, url: str):
        """
        Parse da canonical URL com análise usando helpers seguros
        """
        canonical = self.safe_find(soup, 'link', {'rel': 'canonical'})
        
        if canonical:
            canonical_url = self.safe_get_attribute(canonical, 'href')
            
            # Dados básicos
            data['canonical_url'] = canonical_url
            data['canonical_is_self'] = canonical_url == url
            data['has_canonical'] = True
            
            # Análise adicional usando helpers
            data['canonical_is_empty'] = self.is_empty_text(canonical_url)
            data['canonical_is_valid'] = self.is_valid_url(canonical_url)
            data['canonical_is_relative'] = canonical_url and not canonical_url.startswith(('http://', 'https://'))
            
            # Verifica se canonical aponta para domínio diferente usando helper
            data['canonical_cross_domain'] = not self.is_same_domain(url, canonical_url) and canonical_url != ''
            
            # Análise de HTTPS
            data['canonical_uses_https'] = canonical_url.startswith('https://')
            
        else:
            # Sem canonical
            data['canonical_url'] = ''
            data['canonical_is_self'] = False
            data['has_canonical'] = False
            data['canonical_is_empty'] = True
            data['canonical_is_valid'] = False
            data['canonical_is_relative'] = False
            data['canonical_cross_domain'] = False
            data['canonical_uses_https'] = False
    
    def _parse_meta_robots(self, soup: BeautifulSoup, data: Dict):
        """
        Parse completo da meta robots com todas as diretivas usando helpers seguros
        """
        meta_robots = self.find_meta_by_name(soup, 'robots')
        
        if meta_robots:
            robots_content = self.extract_meta_content(meta_robots).lower()
            
            # Conteúdo completo
            data['meta_robots'] = robots_content
            
            # Diretivas principais
            data['meta_robots_noindex'] = 'noindex' in robots_content
            data['meta_robots_nofollow'] = 'nofollow' in robots_content
            
            # Diretivas adicionais
            data['meta_robots_noarchive'] = 'noarchive' in robots_content
            data['meta_robots_nosnippet'] = 'nosnippet' in robots_content
            data['meta_robots_noimageindex'] = 'noimageindex' in robots_content
            data['meta_robots_none'] = 'none' in robots_content
            
            # Análise de problemas
            data['meta_robots_blocks_indexing'] = data['meta_robots_noindex'] or data['meta_robots_none']
            data['meta_robots_blocks_following'] = data['meta_robots_nofollow'] or data['meta_robots_none']
            
        else:
            # Sem meta robots (comportamento padrão = index, follow)
            data['meta_robots'] = ''
            data['meta_robots_noindex'] = False
            data['meta_robots_nofollow'] = False
            data['meta_robots_noarchive'] = False
            data['meta_robots_nosnippet'] = False
            data['meta_robots_noimageindex'] = False
            data['meta_robots_none'] = False
            data['meta_robots_blocks_indexing'] = False
            data['meta_robots_blocks_following'] = False
    
    # ==========================================
    # MÉTODOS AUXILIARES PARA ANÁLISE
    # ==========================================
    
    def get_meta_summary(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera resumo dos problemas meta encontrados
        
        Args:
            parsed_data: Dados já parseados pelo método parse()
            
        Returns:
            Dict com resumo de problemas meta
        """
        problems = []
        
        # Problemas de title
        if parsed_data.get('title_is_empty'):
            problems.append('Título ausente')
        elif parsed_data.get('title_too_long'):
            problems.append('Título muito longo (>60 chars)')
        elif parsed_data.get('title_too_short'):
            problems.append('Título muito curto (<30 chars)')
        
        # Problemas de meta description
        if parsed_data.get('meta_description_is_empty'):
            problems.append('Meta description ausente')
        elif parsed_data.get('meta_description_too_long'):
            problems.append('Meta description muito longa (>160 chars)')
        elif parsed_data.get('meta_description_too_short'):
            problems.append('Meta description muito curta (<120 chars)')
        
        # Problemas de canonical
        if not parsed_data.get('has_canonical'):
            problems.append('Canonical URL ausente')
        elif parsed_data.get('canonical_is_empty'):
            problems.append('Canonical URL vazia')
        elif parsed_data.get('canonical_cross_domain'):
            problems.append('Canonical aponta para domínio externo')
        
        # Problemas de indexação
        if parsed_data.get('meta_robots_blocks_indexing'):
            problems.append('Página bloqueada para indexação')
        
        return {
            'meta_problems_count': len(problems),
            'meta_problems_list': problems,
            'meta_has_critical_issues': any('ausente' in p or 'bloqueada' in p for p in problems)
        }
    
    def validate_meta_best_practices(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida boas práticas de meta tags usando os novos campos
        
        Args:
            parsed_data: Dados já parseados
            
        Returns:
            Dict com validações de boas práticas
        """
        validations = {}
        
        # Title best practices (usando novos campos)
        validations['title_optimal_length'] = parsed_data.get('title_optimal_length', False)
        validations['title_has_brand'] = parsed_data.get('title_has_brand', False)
        validations['title_not_empty'] = not parsed_data.get('title_is_empty', True)
        
        # Meta description best practices (usando novos campos)
        validations['meta_desc_optimal_length'] = parsed_data.get('meta_description_optimal_length', False)
        validations['meta_desc_not_empty'] = not parsed_data.get('meta_description_is_empty', True)
        
        # Canonical best practices (usando novos campos)
        validations['has_canonical'] = parsed_data.get('has_canonical', False)
        validations['canonical_is_self_referencing'] = parsed_data.get('canonical_is_self', False)
        validations['canonical_uses_https'] = parsed_data.get('canonical_uses_https', False)
        validations['canonical_not_cross_domain'] = not parsed_data.get('canonical_cross_domain', False)
        
        # Robots best practices
        validations['not_blocking_indexing'] = not parsed_data.get('meta_robots_blocks_indexing', False)
        validations['not_blocking_following'] = not parsed_data.get('meta_robots_blocks_following', False)
        
        # Score geral (0-100) - mais critérios agora
        score_items = [
            validations['title_optimal_length'],
            validations['title_not_empty'],
            validations['meta_desc_optimal_length'],
            validations['meta_desc_not_empty'],
            validations['has_canonical'],
            validations['canonical_is_self_referencing'],
            validations['canonical_uses_https'],
            validations['not_blocking_indexing']
        ]
        
        validations['meta_best_practices_score'] = int((sum(score_items) / len(score_items)) * 100)
        
        return validations

# ==========================================
# FUNÇÃO STANDALONE PARA TESTES
# ==========================================

def parse_meta_elements(html_content: str, url: str = 'https://example.com') -> Dict[str, Any]:
    """
    Função standalone para testar o MetaParser com ParserMixin
    
    Args:
        html_content: HTML da página
        url: URL da página (para canonical comparison)
        
    Returns:
        Dict com dados meta parseados
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'lxml')
    parser = MetaParser()
    
    # Parse básico
    data = parser.parse(soup, url)
    
    # Adiciona análises extras
    data.update(parser.get_meta_summary(data))
    data.update(parser.validate_meta_best_practices(data))
    
    return data

# ==========================================
# EXEMPLO DE USO E TESTE
# ==========================================

if __name__ == "__main__":
    # Teste com HTML de exemplo
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Título de Teste da Página | Minha Marca</title>
        <meta name="description" content="Esta é uma meta description de teste com tamanho adequado para verificar se o parser está funcionando corretamente.">
        <meta name="keywords" content="seo, parser, teste, meta tags">
        <link rel="canonical" href="https://example.com/teste">
        <meta name="robots" content="index, follow">
    </head>
    <body>
        <h1>Conteúdo da página</h1>
    </body>
    </html>
    """
    
    # Parse e resultado
    result = parse_meta_elements(test_html, 'https://example.com/teste')
    
    print("🔍 RESULTADO DO META PARSER REFATORADO:")
    print(f"   Title: {result['title']} ({result['title_length']} chars)")
    print(f"   Title Optimal: {result['title_optimal_length']}")
    print(f"   Meta Desc: {result['meta_description'][:50]}... ({result['meta_description_length']} chars)")
    print(f"   Meta Desc Optimal: {result['meta_description_optimal_length']}")
    print(f"   Canonical: {result['canonical_url']}")
    print(f"   Canonical Valid: {result['canonical_is_valid']}")
    print(f"   Canonical HTTPS: {result['canonical_uses_https']}")
    print(f"   Robots: {result['meta_robots']}")
    print(f"   Score: {result['meta_best_practices_score']}/100")
    print(f"   Problemas: {result['meta_problems_count']}")
    if result['meta_problems_list']:
        for problem in result['meta_problems_list']:
            print(f"      - {problem}")