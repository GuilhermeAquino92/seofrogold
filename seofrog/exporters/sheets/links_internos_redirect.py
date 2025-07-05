"""
PATCH 3: seofrog/exporters/sheets/links_internos_redirect.py
Versão robusta com todas as correções e melhorias
"""

import pandas as pd
from .base_sheet import BaseSheet

class LinksInternosRedirectSheet(BaseSheet):
    """
    Sheet específica para links internos com redirects (padrão Screaming Frog)
    ✅ VERSÃO ROBUSTA: Blindagem contra None, validação, logs informativos
    """
    
    def get_sheet_name(self) -> str:
        return 'Internal'
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria aba Internal com links internos que fazem redirect
        ✅ CORRIGIDO: Agora processa dados específicos por URL
        """
        try:
            redirect_issues = []
            processed_urls = 0
            total_redirects_found = 0
            
            # Debug: Log estrutura dos dados
            self.logger.debug(f"Analisando {len(df)} URLs para redirects")
            self.logger.debug(f"Colunas disponíveis: {list(df.columns)}")
            
            # ✅ Processa dados específicos por URL (CORREÇÃO PRINCIPAL)
            if 'internal_redirects_details' in df.columns:
                self.logger.debug("Processando coluna 'internal_redirects_details'...")
                
                for idx, row in df.iterrows():
                    processed_urls += 1
                    url = str(row.get('url', f'URL_{idx}'))
                    redirects_data = row.get('internal_redirects_details', [])
                    
                    # ✅ Validação robusta
                    if not isinstance(redirects_data, list):
                        self.logger.debug(f"Dados de redirect inválidos para {url}: {type(redirects_data)}")
                        continue
                    
                    if not redirects_data:
                        continue  # URL sem redirects
                    
                    self.logger.debug(f"Processando {len(redirects_data)} redirects de {url}")
                    
                    for redirect in redirects_data:
                        if not isinstance(redirect, dict):
                            self.logger.warning(f"Redirect malformado em {url}: {type(redirect)}")
                            continue
                        
                        # ✅ Extração segura com blindagem contra None
                        try:
                            redirect_item = self._extract_redirect_data(redirect, url)
                            if redirect_item:
                                redirect_issues.append(redirect_item)
                                total_redirects_found += 1
                        except Exception as e:
                            self.logger.warning(f"Erro extraindo redirect de {url}: {e}")
                            continue
            
            # ✅ Fallback: Analisa redirects básicos se não encontrou dados específicos
            if not redirect_issues and self._has_basic_redirect_data(df):
                self.logger.info("Fallback: analisando redirects básicos (URL != final_URL)")
                redirect_issues = self._process_basic_redirects(df)
                total_redirects_found = len(redirect_issues)
            
            # ✅ Criação da planilha com dados validados
            self._create_excel_output(redirect_issues, writer, processed_urls, total_redirects_found)
                
        except Exception as e:
            self.logger.error(f"Erro criando aba Internal: {e}")
            self._create_error_sheet(writer, f'Erro na análise de links internos: {str(e)}')
    
    def _extract_redirect_data(self, redirect: dict, source_url: str) -> dict:
        """
        ✅ Extrai dados de redirect com validação robusta e blindagem contra None
        """
        # ✅ Validação: campos obrigatórios
        required_fields = ['From', 'To (Final)', 'Código']
        missing_fields = [field for field in required_fields if not redirect.get(field)]
        
        if missing_fields:
            self.logger.debug(f"Redirect ignorado (campos faltando {missing_fields}): {redirect}")
            return None
        
        # ✅ Extração segura com str() para evitar None.strip()
        from_url = str(redirect.get('From', source_url) or source_url)
        to_url = str(redirect.get('To (Final)', redirect.get('To (Original)', '')) or '')
        anchor_text = str(redirect.get('Anchor', '') or '').strip()
        status_code = redirect.get('Código', '')
        
        # ✅ Validação de URL válida
        if not to_url or to_url == from_url:
            self.logger.debug(f"Redirect inválido: {from_url} → {to_url}")
            return None
        
        # ✅ Log quando encontra anchor text
        if anchor_text:
            self.logger.debug(f"Anchor text encontrado: '{anchor_text}' ({from_url} → {to_url})")
        
        return {
            'Type': 'Hyperlink',
            'From': from_url,
            'To': to_url,
            'Anchor Text': anchor_text,
            'Link Path': str(redirect.get('Link Path', '') or self._get_default_path()),
            'Alt Text': str(redirect.get('Alt Text', '') or '').strip(),
            'Follow': str(redirect.get('Follow', 'True')),
            'Target': str(redirect.get('Target', '') or '').strip(),
            'Rel': str(redirect.get('Rel', '') or '').strip(),
            'Status Code': status_code,
            'Status': self._get_status_text(status_code)
        }
    
    def _has_basic_redirect_data(self, df: pd.DataFrame) -> bool:
        """
        ✅ Verifica se DataFrame tem dados básicos para detectar redirects
        """
        required_cols = ['url', 'final_url', 'status_code']
        has_cols = all(col in df.columns for col in required_cols)
        
        if has_cols:
            # Verifica se há pelo menos um redirect
            redirects_count = len(df[df['url'] != df['final_url']])
            return redirects_count > 0
        
        return False
    
    def _process_basic_redirects(self, df: pd.DataFrame) -> list:
        """
        ✅ Processa redirects básicos quando dados específicos não estão disponíveis
        """
        basic_redirects = []
        
        for _, row in df.iterrows():
            url = str(row.get('url', ''))
            final_url = str(row.get('final_url', ''))
            status_code = row.get('status_code', 200)
            
            # Detecta redirect
            if url != final_url and url and final_url:
                # Tenta obter anchor text de campos disponíveis
                anchor_text = self._extract_anchor_from_row(row)
                
                basic_redirects.append({
                    'Type': 'Hyperlink',
                    'From': url,
                    'To': final_url,
                    'Anchor Text': anchor_text,
                    'Link Path': self._get_default_path(),
                    'Alt Text': '',
                    'Follow': 'True',
                    'Target': '',
                    'Rel': '',
                    'Status Code': status_code,
                    'Status': self._get_status_text(status_code)
                })
                
                if anchor_text:
                    self.logger.debug(f"Anchor básico: '{anchor_text}' ({url} → {final_url})")
        
        return basic_redirects
    
    def _create_excel_output(self, redirect_issues: list, writer, processed_urls: int, total_redirects: int):
        """
        ✅ Cria saída Excel com logs informativos
        """
        if redirect_issues:
            # Define ordem das colunas Screaming Frog
            column_order = [
                'Type', 'From', 'To', 'Anchor Text', 'Link Path', 'Alt Text', 
                'Follow', 'Target', 'Rel', 'Status Code', 'Status'
            ]
            
            # Cria DataFrame
            redirects_df = pd.DataFrame(redirect_issues)
            
            # ✅ Garante que todas as colunas existem
            for col in column_order:
                if col not in redirects_df.columns:
                    redirects_df[col] = ''
            
            # Reordena, remove duplicatas e ordena
            redirects_df = redirects_df[column_order]
            redirects_df = redirects_df.drop_duplicates(subset=['From', 'To'], keep='first')
            redirects_df = redirects_df.sort_values(['Status Code', 'From'])
            
            # Exporta
            redirects_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            
            # ✅ Log estatísticas detalhadas
            anchors_found = sum(1 for _, row in redirects_df.iterrows() if str(row['Anchor Text']).strip())
            paths_found = sum(1 for _, row in redirects_df.iterrows() if str(row['Link Path']).strip())
            
            self.logger.info(f"✅ {self.get_sheet_name()}: {len(redirects_df)} redirects exportados")
            self.logger.info(f"   📊 URLs processadas: {processed_urls}")
            self.logger.info(f"   📝 Anchor text: {anchors_found}/{len(redirects_df)} preenchidos")
            self.logger.info(f"   🔗 Link paths: {paths_found}/{len(redirects_df)} preenchidos")
            
            # ✅ Estatísticas por status code
            status_counts = redirects_df['Status Code'].value_counts()
            if len(status_counts) > 0:
                self.logger.info(f"   📈 Status codes: {dict(status_counts.head(3))}")
            
        else:
            # Nenhum redirect encontrado
            success_df = pd.DataFrame([
                ['No redirects found', '', '', '', '', '', '', '', '', '', '']
            ], columns=[
                'Type', 'From', 'To', 'Anchor Text', 'Link Path', 'Alt Text', 
                'Follow', 'Target', 'Rel', 'Status Code', 'Status'
            ])
            success_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            self.logger.info(f"✅ {self.get_sheet_name()}: Nenhum redirect encontrado ({processed_urls} URLs analisadas)")
    
    def _get_status_text(self, status_code) -> str:
        """
        ✅ Converte código HTTP em texto descritivo com validação
        """
        status_map = {
            200: 'OK',
            301: 'Moved Permanently',
            302: 'Found',
            303: 'See Other',
            307: 'Temporary Redirect',
            308: 'Permanent Redirect',
            400: 'Bad Request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Not Found',
            410: 'Gone',
            500: 'Internal Server Error',
            502: 'Bad Gateway',
            503: 'Service Unavailable',
            504: 'Gateway Timeout'
        }
        
        try:
            if isinstance(status_code, (int, float)):
                code = int(status_code)
                return status_map.get(code, f'HTTP {code}')
            elif isinstance(status_code, str) and status_code.isdigit():
                code = int(status_code)
                return status_map.get(code, f'HTTP {code}')
            else:
                return str(status_code) if status_code else 'Unknown'
        except (ValueError, TypeError):
            return str(status_code) if status_code else 'Unknown'
    
    def _extract_anchor_from_row(self, row) -> str:
        """
        ✅ Extrai anchor text de campos disponíveis com blindagem
        """
        fields = ['anchor_text', 'anchor', 'link_text', 'title', 'h1_text']
        
        for field in fields:
            value = row.get(field, '')
            if value and str(value).strip():
                result = str(value).strip()
                self.logger.debug(f"Anchor extraído de '{field}': '{result}'")
                return result
        
        return ''
    
    def _get_default_path(self) -> str:
        """
        ✅ Retorna link path padrão quando não disponível
        """
        return '/body/div[1]/div/div[1]/div/div[1]/section/div/div/div/div[1]/div/div/div/a[1]'