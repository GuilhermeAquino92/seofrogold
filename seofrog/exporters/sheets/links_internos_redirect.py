"""
seofrog/exporters/sheets/links_internos_redirect.py
Aba específica para Links Internos com Redirecionamento
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
            # Primeiro, criamos um mapeamento de URLs que redirecionam
            redirect_mapping = self._build_redirect_mapping(df)
            
            if not redirect_mapping:
                self._create_success_sheet(writer, '✅ Nenhum redirecionamento interno detectado!')
                return
            
            # Detecta links problemáticos
            problem_links = self._detect_problematic_links(df, redirect_mapping)
            
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
    
    def _build_redirect_mapping(self, df: pd.DataFrame) -> dict:
        """
        Constrói mapeamento de URLs que redirecionam
        NOVA VERSÃO: Usa dados já resolvidos do parser melhorado
        
        Returns:
            dict: {url_original: redirect_info}
        """
        redirect_mapping = {}
        
        for _, row in df.iterrows():
            # Primeiro verifica se há dados detalhados de links internos
            internal_links_detailed = row.get('internal_links_detailed', [])
            
            if internal_links_detailed and isinstance(internal_links_detailed, list):
                # Usa dados já resolvidos do parser melhorado
                for link_info in internal_links_detailed:
                    if link_info.get('has_redirect', False):
                        url = link_info['url']
                        redirect_mapping[url] = {
                            'final_url': link_info['final_url'],
                            'status_code': link_info['status_code'],
                            'redirect_type': link_info['redirect_type'],
                            'response_time': link_info.get('response_time', 0)
                        }
            else:
                # Fallback: método tradicional usando status_code e final_url da página
                url = row.get('url', '')
                final_url = row.get('final_url', '')
                status_code = row.get('status_code', 200)
                
                if (url and final_url and url != final_url) or status_code in [301, 302, 303, 307, 308]:
                    target_url = final_url if final_url and final_url != url else url
                    redirect_mapping[url] = {
                        'final_url': target_url,
                        'status_code': status_code,
                        'redirect_type': self._classify_redirect_type(url, target_url),
                        'response_time': row.get('response_time', 0)
                    }
        
        self.logger.debug(f"Mapeamento construído: {len(redirect_mapping)} redirects detectados")
        return redirect_mapping
    
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
            
            # Fragment
            if (parsed_orig.netloc == parsed_final.netloc and 
                parsed_orig.path == parsed_final.path and 
                parsed_orig.fragment != parsed_final.fragment):
                return 'Fragment'
            
            # Path redirect
            if (parsed_orig.netloc == parsed_final.netloc and 
                parsed_orig.path != parsed_final.path):
                return 'Path Redirect'
            
            return 'Outro'
            
        except Exception:
            return 'Outro'
    
    def _detect_problematic_links(self, df: pd.DataFrame, redirect_mapping: dict) -> list:
        """
        Detecta links internos que apontam para URLs que redirecionam
        NOVA VERSÃO: Usa dados já resolvidos do parser melhorado
        """
        problem_links = []
        
        for _, row in df.iterrows():
            pagina_origem = row.get('url', '')
            
            # Método melhorado: usa dados já resolvidos
            internal_links_detailed = row.get('internal_links_detailed', [])
            
            if internal_links_detailed and isinstance(internal_links_detailed, list):
                # Usa dados já processados pelo parser melhorado
                for link_info in internal_links_detailed:
                    if link_info.get('has_redirect', False):
                        link_url = link_info['url']
                        final_url = link_info['final_url']
                        status_code = link_info['status_code']
                        redirect_type = link_info['redirect_type']
                        anchor_text = link_info.get('anchor', '')
                        response_time = link_info.get('response_time', 0)
                        
                        # Determina criticidade
                        criticidade = self._determine_criticality(redirect_type, status_code)
                        
                        problem_links.append({
                            'pagina_origem': pagina_origem,
                            'url_linkada': link_url,
                            'destino_final': final_url,
                            'codigo_redirect': status_code,
                            'tipo_problema': self._format_redirect_type(redirect_type),
                            'criticidade': criticidade,
                            'anchor_text': anchor_text[:100] if anchor_text else '',
                            'response_time': f"{response_time:.3f}s" if response_time > 0 else '',
                            'solucao': self._suggest_solution(redirect_type),
                            'impacto': self._describe_impact(redirect_type),
                            'tag_html': link_info.get('tag_html', '')[:150]
                        })
            else:
                # Fallback: método tradicional
                internal_links = self._extract_internal_links(row)
                
                for link_info in internal_links:
                    link_url = link_info['url']
                    anchor_text = link_info.get('anchor', '')
                    
                    if link_url in redirect_mapping:
                        redirect_info = redirect_mapping[link_url]
                        final_url = redirect_info['final_url']
                        redirect_type = redirect_info['redirect_type']
                        status_code = redirect_info['status_code']
                        
                        criticidade = self._determine_criticality(redirect_type, status_code)
                        
                        problem_links.append({
                            'pagina_origem': pagina_origem,
                            'url_linkada': link_url,
                            'destino_final': final_url,
                            'codigo_redirect': status_code,
                            'tipo_problema': self._format_redirect_type(redirect_type),
                            'criticidade': criticidade,
                            'anchor_text': anchor_text[:100] if anchor_text else '',
                            'response_time': '',
                            'solucao': self._suggest_solution(redirect_type),
                            'impacto': self._describe_impact(redirect_type),
                            'tag_html': ''
                        })
        
        return problem_links
    
    def _extract_internal_links(self, row: pd.Series) -> list:
        """
        Extrai links internos de diferentes colunas possíveis
        """
        internal_links = []
        
        # Tenta extrair de diferentes formatos possíveis
        # Formato 1: Lista direta
        if 'internal_links' in row and row['internal_links']:
            links_data = row['internal_links']
            if isinstance(links_data, list):
                for link in links_data:
                    if isinstance(link, dict):
                        internal_links.append(link)
                    elif isinstance(link, str):
                        internal_links.append({'url': link, 'anchor': ''})
            elif isinstance(links_data, str):
                # Se for string, pode ser CSV ou JSON
                try:
                    # Tenta como lista separada por vírgula
                    links = [link.strip() for link in links_data.split(',') if link.strip()]
                    for link in links:
                        internal_links.append({'url': link, 'anchor': ''})
                except:
                    pass
        
        # Formato 2: Colunas separadas (se existirem)
        for col in ['internal_links_list', 'links_internos', 'links_list']:
            if col in row and row[col]:
                try:
                    data = row[col]
                    if isinstance(data, list):
                        for link in data:
                            if isinstance(link, str):
                                internal_links.append({'url': link, 'anchor': ''})
                except:
                    continue
        
        # Remove duplicatas
        seen = set()
        unique_links = []
        for link in internal_links:
            url = link['url']
            if url not in seen:
                seen.add(url)
                unique_links.append(link)
        
        return unique_links
    
    def _format_redirect_type(self, redirect_type: str) -> str:
        """
        Formata tipo de redirect para exibição no Excel
        """
        type_mapping = {
            'HTTP_to_HTTPS': 'HTTP → HTTPS',
            'HTTPS_to_HTTP': 'HTTPS → HTTP (Crítico)',
            'Case_Change': 'Capitalização',
            'Trailing_Slash': 'Trailing Slash',
            'Query_String': 'Query String',
            'WWW_Redirect': 'WWW Redirect',
            'Path_Change': 'Mudança de Path',
            'Domain_Change': 'Mudança de Domínio',
            'Other': 'Outro',
            'Unknown': 'Desconhecido',
            'Error': 'Erro na verificação'
        }
        return type_mapping.get(redirect_type, redirect_type)

    def _determine_criticality(self, redirect_type: str, status_code: int) -> str:
        """
        Determina criticidade do problema - VERSÃO MELHORADA
        """
        # HTTPS -> HTTP é sempre crítico (perda de segurança)
        if redirect_type == 'HTTPS_to_HTTP':
            return 'CRÍTICO'
            
        # HTTP -> HTTPS é alto (SEO e segurança)
        if redirect_type == 'HTTP_to_HTTPS':
            return 'ALTO'
        
        # Mudança de domínio é crítica
        if redirect_type == 'Domain_Change':
            return 'CRÍTICO'
        
        # Path changes com 301 são altos
        if redirect_type == 'Path_Change' and status_code == 301:
            return 'ALTO'
        
        # Case changes e trailing slash são médios mas importantes
        if redirect_type in ['Case_Change', 'Trailing_Slash']:
            return 'MÉDIO'
        
        # WWW redirects são baixos
        if redirect_type == 'WWW_Redirect':
            return 'BAIXO'
        
        # Query string e fragment são baixos
        if redirect_type in ['Query_String']:
            return 'BAIXO'
        
        # Erro na verificação
        if redirect_type == 'Error':
            return 'BAIXO'
        
        # Default baseado no status code
        if status_code == 301:
            return 'MÉDIO'
        elif status_code in [302, 307, 308]:
            return 'BAIXO'
        else:
            return 'BAIXO'

    def _suggest_solution(self, redirect_type: str) -> str:
        """
        Sugere solução para cada tipo de problema - VERSÃO MELHORADA
        """
        solutions = {
            'HTTP_to_HTTPS': 'Alterar links para usar HTTPS diretamente',
            'HTTPS_to_HTTP': 'URGENTE: Corrigir links para manter HTTPS',
            'Case_Change': 'Corrigir capitalização no link (SEO)',
            'Trailing_Slash': 'Padronizar links com/sem trailing slash',
            'Query_String': 'Remover query strings desnecessárias',
            'WWW_Redirect': 'Padronizar links com/sem www',
            'Path_Change': 'Atualizar link para nova estrutura de URLs',
            'Domain_Change': 'Verificar se mudança de domínio é intencional',
            'Other': 'Verificar e corrigir redirecionamento',
            'Unknown': 'Investigar causa do redirecionamento',
            'Error': 'Verificar se URL está acessível'
        }
        return solutions.get(redirect_type, 'Corrigir link para evitar redirect')

    def _describe_impact(self, redirect_type: str) -> str:
        """
        Descreve o impacto de cada tipo de problema - VERSÃO MELHORADA
        """
        impacts = {
            'HTTP_to_HTTPS': 'Perda de link juice + problemas de segurança',
            'HTTPS_to_HTTP': 'CRÍTICO: Perda de segurança + link juice',
            'Case_Change': 'Redirect desnecessário + diluição de autoridade',
            'Trailing_Slash': 'Redirect desnecessário + inconsistência',
            'Query_String': 'Redirect desnecessário + possível tracking',
            'WWW_Redirect': 'Redirect desnecessário + crawl budget',
            'Path_Change': 'Perda de link juice + crawl budget',
            'Domain_Change': 'Possível perda total de link juice',
            'Other': 'Redirect desnecessário + crawl budget',
            'Unknown': 'Impacto desconhecido',
            'Error': 'Link possivelmente quebrado'
        }
        return impacts.get(redirect_type, 'Redirect desnecessário')