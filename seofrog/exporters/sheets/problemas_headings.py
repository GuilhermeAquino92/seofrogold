"""
seofrog/exporters/sheets/problemas_headings.py
Aba específica para análise DOM de headings - identifica elementos vazios ou escondidos por CSS
"""

import pandas as pd
import re
from .base_sheet import BaseSheet

class ProblemasHeadingsSheet(BaseSheet):
    """
    Sheet com análise DOM profunda de headings
    Identifica headings vazios, escondidos por CSS, com apenas whitespace, etc.
    """
    
    def get_sheet_name(self) -> str:
        return 'Problemas Headings DOM'
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Análise DOM profunda de headings para identificar problemas estruturais
        """
        try:
            # Filtra apenas páginas com status 200 
            df = self._filter_successful_pages(df)
            
            if df.empty:
                self._create_success_sheet(writer, 'Nenhuma página 200 para analisar')
                return
            
            heading_issues = []
            
            # Analisa cada página individualmente
            for idx, row in df.iterrows():
                url = row.get('url', '')
                html_content = row.get('html_content', '')
                
                if not html_content:
                    self.logger.debug(f"HTML vazio para {url}")
                    continue
                
                # Log para debug - quantos H6s encontra  
                import re
                h6_count = len(re.findall(r'<h6[^>]*>', html_content, re.IGNORECASE))
                if h6_count > 0:
                    self.logger.debug(f"Encontrados {h6_count} H6s em {url}")
                
                # Analisa problemas DOM nos headings
                dom_issues = self._analyze_heading_dom(url, html_content, row)
                heading_issues.extend(dom_issues)
            
            # Exporta resultados
            if heading_issues:
                self._export_consolidated_issues(heading_issues, writer)
            else:
                self._create_success_sheet(writer, 'Estrutura DOM de headings adequada')
                
        except Exception as e:
            self.logger.error(f"Erro analisando DOM de headings: {e}")
            self._create_error_sheet(writer, f'Erro na análise DOM: {str(e)}')
    
    def _analyze_heading_dom(self, url: str, html_content: str, row: pd.Series) -> list:
        """
        Analisa problemas DOM específicos nos headings
        """
        issues = []
        
        try:
            # Analisa cada nível de heading individualmente
            for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                heading_issues = self._analyze_heading_level(url, html_content, level, row)
                issues.extend(heading_issues)
            
            # Analisa problemas estruturais gerais
            structural_issues = self._check_heading_structure(url, html_content, row)
            issues.extend(structural_issues)
            
        except Exception as e:
            self.logger.warning(f"Erro analisando DOM de {url}: {e}")
            
        return issues
    
    def _analyze_heading_level(self, url: str, html_content: str, level: str, row: pd.Series) -> list:
        """
        Analisa todos os headings de um nível específico (h1, h2, etc.)
        """
        issues = []
        
        # Pattern mais robusto que captura:
        # <h6>content</h6>, <h6></h6>, <h6 attrs>content</h6>, etc.
        pattern = f'<{level}([^>]*)>(.*?)</{level}>'
        
        matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            attributes, content = match
            
            # Monta a tag completa para debug
            full_tag = f'<{level}{attributes}>{content}</{level}>'
            
            # Analisa problemas específicos neste heading
            heading_issues = self._check_heading_content(url, level, content, row, full_tag)
            issues.extend(heading_issues)
        
        return issues
    
    def _check_heading_content(self, url: str, heading_level: str, content: str, row: pd.Series, full_tag: str = '') -> list:
        """
        Verifica problemas específicos no conteúdo do heading
        """
        issues = []
        base_info = self._get_url_info(row)
        
        # Remove tags HTML do conteúdo para análise
        clean_content = re.sub(r'<[^>]+>', '', content).strip()
        
        # 1. Heading completamente vazio
        if not clean_content:
            issues.append({
                **base_info,
                'problema': f'{heading_level.upper()} vazio',
                'detalhes': f'Tag {heading_level} sem conteúdo',
                'criticidade': 'CRÍTICO' if heading_level == 'h1' else 'ALTO',
                'heading_level': heading_level.upper(),
                'content_sample': full_tag[:200] if full_tag else content[:100] if content else '[vazio]',
                'html_tag': full_tag[:300] if full_tag else f'<{heading_level}>{content}</{heading_level}>'
            })
        
        # 2. Heading com apenas whitespace/quebras de linha
        elif not clean_content.strip():
            issues.append({
                **base_info,
                'problema': f'{heading_level.upper()} só whitespace',
                'detalhes': f'Tag {heading_level} contém apenas espaços/quebras',
                'criticidade': 'ALTO',
                'heading_level': heading_level.upper(),
                'content_sample': repr(content[:50]),
                'html_tag': full_tag[:300] if full_tag else f'<{heading_level}>{content}</{heading_level}>'
            })
        
        # 3. Heading muito curto (suspeito)
        elif len(clean_content.strip()) < 3:
            issues.append({
                **base_info,
                'problema': f'{heading_level.upper()} muito curto',
                'detalhes': f'Conteúdo: "{clean_content}" ({len(clean_content)} chars)',
                'criticidade': 'MÉDIO',
                'heading_level': heading_level.upper(),
                'content_sample': clean_content,
                'html_tag': full_tag[:300] if full_tag else f'<{heading_level}>{content}</{heading_level}>'
            })
        
        # 4. Heading com apenas números/símbolos (suspeito)
        elif re.match(r'^[\d\s\-_\.#]+$', clean_content.strip()):
            issues.append({
                **base_info,
                'problema': f'{heading_level.upper()} só números/símbolos',
                'detalhes': f'Conteúdo suspeito: "{clean_content}"',
                'criticidade': 'MÉDIO',
                'heading_level': heading_level.upper(),
                'content_sample': clean_content,
                'html_tag': full_tag[:300] if full_tag else f'<{heading_level}>{content}</{heading_level}>'
            })
        
        return issues
    
    def _check_heading_structure(self, url: str, html_content: str, row: pd.Series) -> list:
        """
        Verifica problemas estruturais gerais dos headings
        """
        issues = []
        base_info = self._get_url_info(row)
        
        try:
            # Conta headings por nível
            heading_counts = {}
            for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                pattern = f'<{level}[^>]*>.*?</{level}>'
                matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
                heading_counts[level] = len(matches)
            
            # 1. Múltiplos H1 (problema SEO crítico)
            if heading_counts.get('h1', 0) > 1:
                issues.append({
                    **base_info,
                    'problema': 'Múltiplos H1',
                    'detalhes': f'{heading_counts["h1"]} tags H1 encontradas',
                    'criticidade': 'CRÍTICO',
                    'heading_level': 'H1',
                    'content_sample': f'{heading_counts["h1"]} H1s detectados'
                })
            
            # 2. Nenhum H1
            if heading_counts.get('h1', 0) == 0:
                issues.append({
                    **base_info,
                    'problema': 'Sem H1',
                    'detalhes': 'Página sem tag H1',
                    'criticidade': 'CRÍTICO',
                    'heading_level': 'H1',
                    'content_sample': 'Nenhum H1 encontrado'
                })
            
            # 3. Hierarquia quebrada (H3 sem H2, etc.)
            hierarchy_issues = self._check_heading_hierarchy(heading_counts)
            for hierarchy_issue in hierarchy_issues:
                issues.append({
                    **base_info,
                    **hierarchy_issue
                })
            
            # 4. Headings escondidos por CSS (pattern suspeito)
            hidden_headings = self._detect_hidden_headings(html_content)
            for hidden in hidden_headings:
                issues.append({
                    **base_info,
                    'problema': 'Heading possivelmente escondido',
                    'detalhes': hidden['details'],
                    'criticidade': 'ALTO',
                    'heading_level': hidden['level'],
                    'content_sample': hidden['sample']
                })
                
        except Exception as e:
            self.logger.warning(f"Erro verificando estrutura de {url}: {e}")
            
        return issues
    
    def _check_heading_hierarchy(self, counts: dict) -> list:
        """
        Verifica problemas na hierarquia de headings
        """
        issues = []
        
        # H3 sem H2
        if counts.get('h3', 0) > 0 and counts.get('h2', 0) == 0:
            issues.append({
                'problema': 'H3 sem H2',
                'detalhes': f'{counts["h3"]} H3s sem nenhum H2',
                'criticidade': 'MÉDIO',
                'heading_level': 'H2/H3',
                'content_sample': f'{counts["h3"]} H3s órfãos'
            })
        
        # H4 sem H3
        if counts.get('h4', 0) > 0 and counts.get('h3', 0) == 0:
            issues.append({
                'problema': 'H4 sem H3',
                'detalhes': f'{counts["h4"]} H4s sem nenhum H3',
                'criticidade': 'BAIXO',
                'heading_level': 'H3/H4',
                'content_sample': f'{counts["h4"]} H4s órfãos'
            })
        
        return issues
    
    def _detect_hidden_headings(self, html_content: str) -> list:
        """
        Detecta headings que podem estar escondidos por CSS
        """
        hidden = []
        
        # Patterns suspeitos de CSS inline que escondem elementos
        hidden_patterns = [
            r'<(h[1-6])[^>]*style="[^"]*display:\s*none[^"]*"[^>]*>(.*?)</h[1-6]>',
            r'<(h[1-6])[^>]*style="[^"]*visibility:\s*hidden[^"]*"[^>]*>(.*?)</h[1-6]>',
            r'<(h[1-6])[^>]*style="[^"]*opacity:\s*0[^"]*"[^>]*>(.*?)</h[1-6]>',
            r'<(h[1-6])[^>]*style="[^"]*height:\s*0[^"]*"[^>]*>(.*?)</h[1-6]>',
            r'<(h[1-6])[^>]*style="[^"]*font-size:\s*0[^"]*"[^>]*>(.*?)</h[1-6]>'
        ]
        
        for pattern in hidden_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                heading_tag, content = match
                clean_content = re.sub(r'<[^>]+>', '', content).strip()
                
                hidden.append({
                    'level': heading_tag.upper(),
                    'details': f'Heading {heading_tag.upper()} com CSS que esconde elemento',
                    'sample': clean_content[:50] if clean_content else '[vazio]'
                })
        
        return hidden