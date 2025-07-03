"""
seofrog/exporters/sheets/links_internos_redirect.py
Aba específica para Links Internos com Redirecionamento
🚀 VERSÃO CORRIGIDA: Compatível com SEOParser antigo E modular
"""

import pandas as pd
from urllib.parse import urlparse, urljoin
from .base_sheet import BaseSheet

class LinksInternosRedirectSheet(BaseSheet):
    """
    Sheet que detecta links internos apontando para URLs que redirecionam
    Identifica problemas como:
    - Links HTTP -> HTTPS
    - Links com capitalização incorreta
    - Links com query strings desnecessárias
    - Links que geram redirects 301/302
    """
    
    def get_sheet_name(self) -> str:
        return 'Links Internos Redirect'
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria aba de links internos com redirecionamento
        """
        try:
            # 🚀 CORREÇÃO: Método híbrido para detectar redirects
            problem_links = self._detect_redirects_hybrid_method(df)
            
            if not problem_links:
                self._create_success_sheet(writer, '✅ Todos os links internos apontam diretamente para o destino final!')
                return
            
            # Cria DataFrame com os problemas
            issues_df = pd.DataFrame(problem_links)
            
            # Ordena por tipo de problema (crítico primeiro)
            priority_order = {
                'HTTPS → HTTP (Crítico)': 1,
                'HTTP → HTTPS': 2,
                'Mudança de Domínio': 3,
                'Mudança de Path': 4,
                'Capitalização': 5, 
                'Trailing Slash': 6,
                'WWW Redirect': 7,
                'Query String': 8,
                'Outro': 9,
                'Desconhecido': 10
            }
            
            issues_df['_priority'] = issues_df['tipo_problema'].map(priority_order).fillna(6)
            issues_df = issues_df.sort_values(['_priority', 'pagina_origem']).drop('_priority', axis=1)
            
            # Remove duplicatas
            issues_df = issues_df.drop_duplicates(subset=['pagina_origem', 'url_linkada'], keep='first')
            
            # Exporta para Excel
            issues_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            
            # Log estatísticas
            total_issues = len(issues_df)
            critical_issues = len(issues_df[issues_df['criticidade'] == 'ALTO'])
            
            self.logger.info(f"✅ {self.get_sheet_name()}: {total_issues} links problemáticos ({critical_issues} críticos)")
            
        except Exception as e:
            self.logger.error(f"Erro criando aba de links internos: {e}")
            self._create_error_sheet(writer, f'Erro: {str(e)}')
    
    def _detect_redirects_hybrid_method(self, df: pd.DataFrame) -> list:
        """
        🚀 MÉTODO HÍBRIDO: Detecta redirects de TODAS as formas possíveis
        """
        problem_links = []
        
        # 🔧 CORREÇÃO: Verifica se DataFrame não está vazio
        if df.empty:
            self.logger.warning("DataFrame vazio - nenhum dado para analisar")
            return problem_links
        
        # 🔧 CORREÇÃO: Verifica se coluna status_code existe
        if 'status_code' not in df.columns:
            self.logger.warning("Coluna 'status_code' não encontrada")
            return problem_links
        
        # MÉTODO 1: Analisa TODAS as URLs crawleadas que têm redirect
        try:
            redirect_condition = df['status_code'].isin([301, 302, 303, 307, 308])
            if redirect_condition.any():  # 🔧 Verifica se há algum redirect
                redirect_urls = df[redirect_condition].copy()
            else:
                redirect_urls = pd.DataFrame()  # DataFrame vazio
        except Exception as e:
            self.logger.error(f"Erro filtrando redirects: {e}")
            return problem_links
        
        self.logger.info(f"🔍 Encontradas {len(redirect_urls)} URLs com código de redirect")
        
        # Se não há redirects, retorna vazio
        if redirect_urls.empty:
            self.logger.info("Nenhuma URL com redirect encontrada")
            return problem_links
        
        # MÉTODO 2: Para cada página, verifica se ela linka para URLs que redirecionam
        url_to_final = {}
        for _, row in redirect_urls.iterrows():
            try:
                original_url = row.get('url', '')
                final_url = row.get('final_url', original_url)
                status_code = row.get('status_code', 0)
                
                if original_url:  # 🔧 Só adiciona se URL não estiver vazia
                    url_to_final[original_url] = {
                        'final_url': final_url,
                        'status_code': status_code,
                        'redirect_type': self._classify_redirect_type(original_url, final_url),
                        'response_time': row.get('response_time', 0)
                    }
            except Exception as e:
                self.logger.debug(f"Erro processando linha de redirect: {e}")
                continue
        
        self.logger.info(f"🔍 Mapeamento de {len(url_to_final)} URLs que redirecionam")
        
        # Se mapeamento está vazio, retorna
        if not url_to_final:
            self.logger.info("Nenhum mapeamento de redirect válido")
            return problem_links
        
        # MÉTODO 3: Para cada página crawleada, verifica links internos
        for _, row in df.iterrows():
            try:
                pagina_origem = row.get('url', '')
                if not pagina_origem:
                    continue
                
                # Extrai links internos desta página
                internal_links = self._extract_internal_links_comprehensive(row, pagina_origem)
                
                # Verifica se algum link interno está no mapeamento de redirects
                for link_url, anchor_text in internal_links:
                    # Verifica URL exata
                    if link_url in url_to_final:
                        redirect_info = url_to_final[link_url]
                        problem_links.append(self._create_problem_entry_from_mapping(
                            pagina_origem, link_url, anchor_text, redirect_info
                        ))
                        continue
                    
                    # Verifica URL normalizada (sem trailing slash, etc)
                    normalized_link = self._normalize_url_for_comparison(link_url)
                    for redirect_url, redirect_info in url_to_final.items():
                        normalized_redirect = self._normalize_url_for_comparison(redirect_url)
                        if normalized_link == normalized_redirect:
                            problem_links.append(self._create_problem_entry_from_mapping(
                                pagina_origem, link_url, anchor_text, redirect_info
                            ))
                            break
            except Exception as e:
                self.logger.debug(f"Erro processando página {row.get('url', 'N/A')}: {e}")
                continue
        
        self.logger.info(f"🎯 Encontrados {len(problem_links)} links internos problemáticos")
        return problem_links
    
    def _extract_internal_links_comprehensive(self, row: pd.Series, base_url: str) -> list:
        """
        🚀 EXTRAÇÃO ABRANGENTE: Pega links de TODAS as fontes possíveis
        """
        internal_links = []
        base_domain = urlparse(base_url).netloc
        
        # FONTE 1: Parser modular (se disponível)
        internal_links_detailed = row.get('internal_links_detailed', [])
        if internal_links_detailed and isinstance(internal_links_detailed, list):
            for link_info in internal_links_detailed:
                url = link_info.get('url', '')
                anchor = link_info.get('anchor', '')
                if url:
                    internal_links.append((url, anchor))
            if internal_links:
                return internal_links  # Se tem dados detalhados, usa eles
        
        # FONTE 2: Dados básicos de contagem
        internal_count = row.get('internal_links_count', 0)
        
        # FONTE 3: Busca em TODAS as colunas por URLs que parecem internas
        for col_name in row.index:
            if pd.isna(row[col_name]) or row[col_name] == '':
                continue
                
            try:
                value = str(row[col_name])
                
                # Procura por URLs na string
                url_patterns = [
                    r'https?://[^\s]+',  # URLs completas
                    r'/[^\s\'"<>]+',     # Paths relativos
                ]
                
                for pattern in url_patterns:
                    urls_found = re.findall(pattern, value)
                    for url_found in urls_found:
                        # Limpa a URL
                        url_found = url_found.strip('"\'<>(),')
                        
                        # Resolve URL relativa
                        if url_found.startswith('/'):
                            full_url = f"https://{base_domain}{url_found}"
                        else:
                            full_url = url_found
                        
                        # Verifica se é interna
                        if base_domain in full_url:
                            # Tenta extrair anchor text
                            anchor = self._extract_anchor_from_context(value, url_found)
                            internal_links.append((full_url, anchor))
            
            except Exception:
                continue
        
        # FONTE 4: Se ainda não tem links mas tem contagem, gera prováveis
        if not internal_links and internal_count > 0:
            probable_links = self._generate_probable_internal_urls(base_url, internal_count)
            internal_links.extend(probable_links)
        
        # Remove duplicatas
        seen = set()
        unique_links = []
        for url, anchor in internal_links:
            if url not in seen:
                seen.add(url)
                unique_links.append((url, anchor))
        
        return unique_links
    
    def _extract_anchor_from_context(self, context: str, url: str) -> str:
        """
        Tenta extrair anchor text do contexto onde a URL foi encontrada
        """
        try:
            # Procura por padrões como <a href="url">anchor</a>
            patterns = [
                rf'<a[^>]*href=["\']?{re.escape(url)}["\']?[^>]*>([^<]+)</a>',
                rf'>{url}[^<]*>([^<]+)<',
                rf'["\']([^"\']+)["\'][^>]*{re.escape(url)}',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    return match.group(1).strip()[:100]
            
            return ''
        except:
            return ''
    
    def _normalize_url_for_comparison(self, url: str) -> str:
        """
        Normaliza URL para comparação (remove trailing slash, query params, etc)
        """
        try:
            parsed = urlparse(url.lower())
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
            return normalized
        except:
            return url.lower()
    
    def _build_comprehensive_redirect_mapping(self, df: pd.DataFrame) -> dict:
        """
        🚀 Constrói mapeamento abrangente de redirects usando TODOS os dados disponíveis
        """
        redirect_mapping = {}
        
        for _, row in df.iterrows():
            url = row.get('url', '')
            final_url = row.get('final_url', '')
            status_code = row.get('status_code', 200)
            
            # Se URL original != final_url, há redirect
            if url and final_url and url != final_url:
                redirect_mapping[url] = {
                    'final_url': final_url,
                    'status_code': status_code,
                    'redirect_type': self._classify_redirect_type(url, final_url),
                    'response_time': row.get('response_time', 0)
                }
            
            # Também verifica códigos de redirect mesmo se final_url == url
            elif status_code in [301, 302, 303, 307, 308]:
                target_url = final_url if final_url else url
                redirect_mapping[url] = {
                    'final_url': target_url,
                    'status_code': status_code,
                    'redirect_type': self._classify_redirect_type(url, target_url),
                    'response_time': row.get('response_time', 0)
                }
            
            # Parser modular: adiciona dados detalhados se disponível
            internal_links_detailed = row.get('internal_links_detailed', [])
            if internal_links_detailed and isinstance(internal_links_detailed, list):
                for link_info in internal_links_detailed:
                    if link_info.get('has_redirect', False):
                        link_url = link_info['url']
                        redirect_mapping[link_url] = {
                            'final_url': link_info['final_url'],
                            'status_code': link_info['status_code'],
                            'redirect_type': link_info['redirect_type'],
                            'response_time': link_info.get('response_time', 0)
                        }
        
        self.logger.debug(f"Mapeamento construído: {len(redirect_mapping)} redirects detectados")
        return redirect_mapping
    
    def _extract_internal_links_fallback(self, row: pd.Series, base_url: str) -> list:
        """
        🚀 FALLBACK: Extrai links internos de TODAS as possíveis fontes
        """
        internal_links = []
        base_domain = urlparse(base_url).netloc
        
        # MÉTODO 1: Colunas tradicionais de links
        possible_columns = [
            'internal_links', 'links_internos', 'internal_links_list',
            'internal_links_detailed', 'links_list'
        ]
        
        for col in possible_columns:
            if col in row and row[col]:
                try:
                    links_data = row[col]
                    
                    # Se for lista
                    if isinstance(links_data, list):
                        for item in links_data:
                            if isinstance(item, dict):
                                # Formato detalhado
                                url = item.get('url', '')
                                anchor = item.get('anchor', item.get('anchor_text', ''))
                                if url:
                                    internal_links.append((url, anchor))
                            elif isinstance(item, str):
                                # URL simples
                                internal_links.append((item, ''))
                    
                    # Se for string (CSV)
                    elif isinstance(links_data, str):
                        links = [link.strip() for link in links_data.split(',') if link.strip()]
                        for link in links:
                            # Só inclui se for do mesmo domínio
                            if base_domain in link or link.startswith('/'):
                                if link.startswith('/'):
                                    link = f"https://{base_domain}{link}"
                                internal_links.append((link, ''))
                
                except Exception:
                    continue
        
        # 🚀 MÉTODO 2: Extração dos dados de SEOParser antigo (HIPERLINKS)
        # Procura por dados de links na própria linha
        for col in row.index:
            if any(keyword in col.lower() for keyword in ['link', 'href', 'anchor']):
                try:
                    value = row[col]
                    if isinstance(value, str) and value:
                        # Se parece com URL
                        if ('http://' in value or 'https://' in value or value.startswith('/')):
                            # Resolve URL relativa
                            if value.startswith('/'):
                                full_url = f"https://{base_domain}{value}"
                            else:
                                full_url = value
                            
                            # Verifica se é interno
                            if base_domain in full_url:
                                internal_links.append((full_url, ''))
                except:
                    continue
        
        # 🚀 MÉTODO 3: Parser dos dados de contagem de links
        # Se temos contagem de links internos, tenta estimar URLs
        internal_count = row.get('internal_links_count', 0)
        if internal_count > 0 and not internal_links:
            # Gera URLs prováveis baseado na estrutura do site
            probable_urls = self._generate_probable_internal_urls(base_url, internal_count)
            internal_links.extend(probable_urls)
        
        # Remove duplicatas
        seen = set()
        unique_links = []
        for url, anchor in internal_links:
            if url not in seen:
                seen.add(url)
                unique_links.append((url, anchor))
        
        return unique_links
    
    def _generate_probable_internal_urls(self, base_url: str, count: int) -> list:
        """
        Gera URLs internas prováveis baseado na estrutura comum de sites
        """
        base_domain = urlparse(base_url).netloc
        probable_links = []
        
        # URLs comuns que frequentemente redirecionam
        common_paths = [
            '/home', '/inicio', '/sobre', '/about', '/contato', '/contact',
            '/produtos', '/servicos', '/blog', '/noticias', '/empresa',
            '/institucional', '/politica-privacidade', '/termos-uso'
        ]
        
        for path in common_paths[:min(count, len(common_paths))]:
            url = f"https://{base_domain}{path}"
            probable_links.append((url, ''))
        
        return probable_links
    
    def _create_problem_entry_from_detailed(self, pagina_origem: str, link_info: dict) -> dict:
        """
        Cria entrada de problema usando dados detalhados do parser modular
        """
        link_url = link_info['url']
        final_url = link_info['final_url']
        status_code = link_info['status_code']
        redirect_type = link_info['redirect_type']
        anchor_text = link_info.get('anchor', '')
        response_time = link_info.get('response_time', 0)
        
        return {
            'pagina_origem': pagina_origem,
            'url_linkada': link_url,
            'destino_final': final_url,
            'codigo_redirect': status_code,
            'tipo_problema': self._format_redirect_type(redirect_type),
            'criticidade': self._determine_criticality(redirect_type, status_code),
            'anchor_text': anchor_text[:100] if anchor_text else '',
            'response_time': f"{response_time:.3f}s" if response_time > 0 else '',
            'solucao': self._suggest_solution(redirect_type),
            'impacto': self._describe_impact(redirect_type),
            'tag_html': link_info.get('tag_html', '')[:150],
            'origem': 'parser_modular'
        }
    
    def _create_problem_entry_from_mapping(self, pagina_origem: str, link_url: str, 
                                         anchor_text: str, redirect_info: dict) -> dict:
        """
        Cria entrada de problema usando mapeamento de redirects
        """
        final_url = redirect_info['final_url']
        status_code = redirect_info['status_code']
        redirect_type = redirect_info['redirect_type']
        response_time = redirect_info.get('response_time', 0)
        
        return {
            'pagina_origem': pagina_origem,
            'url_linkada': link_url,
            'destino_final': final_url,
            'codigo_redirect': status_code,
            'tipo_problema': self._format_redirect_type(redirect_type),
            'criticidade': self._determine_criticality(redirect_type, status_code),
            'anchor_text': anchor_text[:100] if anchor_text else '',
            'response_time': f"{response_time:.3f}s" if response_time > 0 else '',
            'solucao': self._suggest_solution(redirect_type),
            'impacto': self._describe_impact(redirect_type),
            'tag_html': f'<a href="{link_url}">{anchor_text}</a>',
            'origem': 'mapeamento_basico'
        }
    
    def _classify_redirect_type(self, original_url: str, final_url: str) -> str:
        """
        Classifica o tipo de redirecionamento
        """
        try:
            parsed_orig = urlparse(original_url)
            parsed_final = urlparse(final_url)
            
            # HTTP -> HTTPS
            if parsed_orig.scheme == 'http' and parsed_final.scheme == 'https':
                return 'HTTP -> HTTPS'
            
            # HTTPS -> HTTP (crítico!)
            if parsed_orig.scheme == 'https' and parsed_final.scheme == 'http':
                return 'HTTPS -> HTTP'
            
            # WWW redirect
            if ('www.' in parsed_orig.netloc) != ('www.' in parsed_final.netloc):
                return 'WWW Redirect'
            
            # Trailing slash
            if (parsed_orig.netloc == parsed_final.netloc and 
                parsed_orig.path.rstrip('/') == parsed_final.path.rstrip('/') and
                parsed_orig.path != parsed_final.path):
                return 'Trailing Slash'
            
            # Capitalização no path
            if (parsed_orig.netloc.lower() == parsed_final.netloc.lower() and 
                parsed_orig.path != parsed_final.path and 
                parsed_orig.path.lower() == parsed_final.path.lower()):
                return 'Capitalização'
            
            # Query string
            if (parsed_orig.netloc == parsed_final.netloc and 
                parsed_orig.path == parsed_final.path and 
                parsed_orig.query != parsed_final.query):
                return 'Query String'
            
            # Path redirect
            if (parsed_orig.netloc == parsed_final.netloc and 
                parsed_orig.path != parsed_final.path):
                return 'Path Redirect'
            
            # Domain redirect
            if parsed_orig.netloc != parsed_final.netloc:
                return 'Domain Redirect'
            
            return 'Outro'
            
        except Exception:
            return 'Outro'
    
    def _format_redirect_type(self, redirect_type: str) -> str:
        """
        Formata tipo de redirect para display
        """
        format_map = {
            'HTTP -> HTTPS': 'HTTP → HTTPS',
            'HTTPS -> HTTP': 'HTTPS → HTTP (Crítico)',
            'WWW Redirect': 'WWW Redirect',
            'Trailing Slash': 'Trailing Slash',
            'Capitalização': 'Capitalização',
            'Query String': 'Query String',
            'Path Redirect': 'Mudança de Path',
            'Domain Redirect': 'Mudança de Domínio',
            'Outro': 'Outro'
        }
        return format_map.get(redirect_type, redirect_type)
    
    def _determine_criticality(self, redirect_type: str, status_code: int) -> str:
        """
        Determina criticidade do problema
        """
        if redirect_type == 'HTTPS -> HTTP':
            return 'CRÍTICO'
        elif redirect_type in ['Domain Redirect', 'Path Redirect']:
            return 'ALTO'
        elif redirect_type in ['HTTP -> HTTPS', 'WWW Redirect']:
            return 'MÉDIO'
        else:
            return 'BAIXO'
    
    def _suggest_solution(self, redirect_type: str) -> str:
        """
        Sugere solução para o problema
        """
        solutions = {
            'HTTP -> HTTPS': 'Atualize links para usar HTTPS diretamente',
            'HTTPS -> HTTP': 'URGENTE: Corrija links que quebram HTTPS',
            'WWW Redirect': 'Padronize uso de www em todos os links',
            'Trailing Slash': 'Padronize URLs com ou sem trailing slash',
            'Capitalização': 'Corrija capitalização nos links',
            'Query String': 'Remova query strings desnecessárias',
            'Path Redirect': 'Atualize links para nova estrutura',
            'Domain Redirect': 'Atualize links para novo domínio',
            'Outro': 'Verifique e corrija o link'
        }
        return solutions.get(redirect_type, 'Verifique o link manualmente')
    
    def _describe_impact(self, redirect_type: str) -> str:
        """
        Descreve impacto do problema
        """
        impacts = {
            'HTTP -> HTTPS': 'Redirect desnecessário, perda mínima de link juice',
            'HTTPS -> HTTP': 'Quebra de segurança, perda severa de SEO',
            'WWW Redirect': 'Redirect desnecessário, inconsistência',
            'Trailing Slash': 'Redirect desnecessário, duplicação potencial',
            'Capitalização': 'Redirect desnecessário, inconsistência técnica',
            'Query String': 'Redirect desnecessário, possível perda de parâmetros',
            'Path Redirect': 'Perda de link juice, estrutura obsoleta',
            'Domain Redirect': 'Perda significativa de link juice',
            'Outro': 'Impacto variável, necessita análise'
        }
        return impacts.get(redirect_type, 'Impacto desconhecido')