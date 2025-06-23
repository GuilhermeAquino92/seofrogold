"""
seofrog/exporters/sheets/mixed_content.py
Aba específica para problemas de Mixed Content - BASEADO NO _create_mixed_content_problems_sheet() ORIGINAL
"""

import pandas as pd
from .base_sheet import BaseSheet

class MixedContentSheet(BaseSheet):
    """
    Sheet com problemas de Mixed Content (HTTPS/HTTP Security)
    Baseado exatamente no método _create_mixed_content_problems_sheet() original
    """
    
    def get_sheet_name(self) -> str:
        return '🔒 Mixed Content'
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria aba de Mixed Content - IDÊNTICO ao método original
        """
        try:
            mixed_content_issues = []
            
            # Filtra apenas páginas HTTPS que têm problemas de mixed content (exatamente como no original)
            if 'is_https_page' in df.columns and 'total_mixed_content_count' in df.columns:
                https_pages_with_issues = df[
                    (df['is_https_page'].fillna(False) == True) & 
                    (df['total_mixed_content_count'].fillna(0) > 0)
                ].copy()
                
                if not https_pages_with_issues.empty:
                    for index, row in https_pages_with_issues.iterrows():
                        url = row.get('url', '')
                        active_count = row.get('active_mixed_content_count', 0)
                        passive_count = row.get('passive_mixed_content_count', 0)
                        risk_level = row.get('mixed_content_risk', 'DESCONHECIDO')
                        
                        # Processa Active Mixed Content (CRÍTICO) (exatamente como no original)
                        active_details = row.get('active_mixed_content_details', [])
                        if active_details and isinstance(active_details, list):
                            for item in active_details:
                                if isinstance(item, dict):
                                    mixed_content_issues.append({
                                        'url': url,
                                        'tipo_mixed_content': 'ACTIVE (Crítico)',
                                        'tipo_recurso': item.get('type', 'unknown').upper(),
                                        'url_http': item.get('url', ''),
                                        'risco': 'CRÍTICO - Bloqueado pelo browser',
                                        'impacto': 'Quebra funcionalidade da página',
                                        'solucao': f'Alterar {item.get("type")} para HTTPS'
                                    })
                        
                        # Processa Passive Mixed Content (AVISO) (exatamente como no original)
                        passive_details = row.get('passive_mixed_content_details', [])
                        if passive_details and isinstance(passive_details, list):
                            for item in passive_details:
                                if isinstance(item, dict):
                                    mixed_content_issues.append({
                                        'url': url,
                                        'tipo_mixed_content': 'PASSIVE (Aviso)',
                                        'tipo_recurso': item.get('type', 'unknown').upper(),
                                        'url_http': item.get('url', ''),
                                        'risco': 'MÉDIO - Cadeado quebrado',
                                        'impacto': 'Reduz confiança do usuário',
                                        'solucao': f'Alterar {item.get("type")} para HTTPS'
                                    })
                        
                        # FALLBACK: Se não há detalhes, usa resumos (exatamente como no original)
                        if (not active_details and active_count > 0) or (not passive_details and passive_count > 0):
                            mixed_content_issues.append({
                                'url': url,
                                'tipo_mixed_content': 'MIXED CONTENT',
                                'tipo_recurso': 'MÚLTIPLOS',
                                'url_http': f'{active_count} active + {passive_count} passive',
                                'risco': risk_level,
                                'impacto': 'Problemas de segurança HTTPS',
                                'solucao': 'Verificar todos os recursos HTTP'
                            })
            
            # Adiciona problemas de Links e Forms HTTP (menos críticos) (exatamente como no original)
            if 'http_links_count' in df.columns or 'http_forms_count' in df.columns:
                http_other_issues = df[
                    (df['http_links_count'].fillna(0) > 0) | 
                    (df['http_forms_count'].fillna(0) > 0)
                ].copy()
                
                for index, row in http_other_issues.iterrows():
                    url = row.get('url', '')
                    links_count = row.get('http_links_count', 0)
                    forms_count = row.get('http_forms_count', 0)
                    
                    if links_count > 0:
                        mixed_content_issues.append({
                            'url': url,
                            'tipo_mixed_content': 'HTTP LINKS',
                            'tipo_recurso': 'LINKS',
                            'url_http': f'{links_count} links HTTP',
                            'risco': 'BAIXO - Não é mixed content',
                            'impacto': 'Usuário pode sair do HTTPS',
                            'solucao': 'Alterar links para HTTPS quando possível'
                        })
                    
                    if forms_count > 0:
                        mixed_content_issues.append({
                            'url': url,
                            'tipo_mixed_content': 'HTTP FORMS',
                            'tipo_recurso': 'FORMS',
                            'url_http': f'{forms_count} forms HTTP',
                            'risco': 'MÉDIO - Dados não criptografados',
                            'impacto': 'Submissão de dados insegura',
                            'solucao': 'URGENTE: Alterar action para HTTPS'
                        })
            
            # Cria DataFrame com os problemas (exatamente como no original)
            if mixed_content_issues:
                issues_df = pd.DataFrame(mixed_content_issues)
                
                # Remove duplicatas (mesma URL + mesmo tipo) (exatamente como no original)
                issues_df = issues_df.drop_duplicates(subset=['url', 'tipo_mixed_content', 'url_http'], keep='first')
                
                # Ordena por criticidade (Active primeiro, depois Passive, depois outros) (exatamente como no original)
                risk_order = {
                    'CRÍTICO - Bloqueado pelo browser': 1, 
                    'MÉDIO - Cadeado quebrado': 2, 
                    'MÉDIO - Dados não criptografados': 3, 
                    'BAIXO - Não é mixed content': 4
                }
                issues_df['_sort_order'] = issues_df['risco'].map(risk_order).fillna(5)
                issues_df = issues_df.sort_values(['_sort_order', 'url']).drop('_sort_order', axis=1)
                
                # Exporta para Excel (exatamente como no original)
                issues_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                
                # Log estatísticas (exatamente como no original)
                total_issues = len(issues_df)
                critical_issues = len(issues_df[issues_df['risco'].str.contains('CRÍTICO')])
                medium_issues = len(issues_df[issues_df['risco'].str.contains('MÉDIO')])
                
                self.logger.info(f"✅ Aba Mixed Content: {total_issues} problemas ({critical_issues} críticos, {medium_issues} médios)")
                
            else:
                # Nenhum problema encontrado (exatamente como no original)
                success_df = pd.DataFrame([
                    ['✅ Nenhum problema de Mixed Content encontrado!'],
                    ['🔒 Todas as páginas HTTPS estão seguras'],
                    ['📋 Verifique se há páginas HTTPS no crawl']
                ], columns=['Status'])
                success_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                self.logger.info(f"✅ {self.get_sheet_name()}: Nenhum problema encontrado")
                
        except Exception as e:
            self.logger.error(f"Erro criando aba de mixed content: {e}")
            error_df = pd.DataFrame([[f'Erro: {str(e)}']], columns=['Erro'])
            error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)