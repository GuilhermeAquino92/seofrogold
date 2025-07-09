import pandas as pd
import json
from typing import List, Dict, Any
from .base_sheet import BaseSheet
from seofrog.utils.logger import get_logger

class LinksInternosRedirectSheet(BaseSheet):
    """
    Aba "Internal" - Apenas links internos com redirects desnecessários (3xx)
    Mostra origem, destino, anchor text e caminho no DOM (Link Path).
    """

    def __init__(self):
        self.logger = get_logger('LinksInternosRedirectSheet')

    def get_sheet_name(self) -> str:
        return "Internal"

    def create_sheet(self, df: pd.DataFrame, writer) -> None:  # ✅ CORRIGIDO: 4 espaços
        """
        ✅ VERSÃO CORRIGIDA - Usa dados de AMBOS os parsers
        """
        try:
            all_redirected_links = []

            for row in df.to_dict(orient="records"):
                
                # 🔧 FONTE 1: LinksParser (original)
                links = row.get("internal_links_details", [])
                if isinstance(links, str):
                    try:
                        links = json.loads(links)
                        redirected_links = [link for link in links if str(link.get('Redirected', '')).lower() == 'true']
                        all_redirected_links.extend(redirected_links)
                    except:
                        pass
                
                # 🆕 FONTE 2: TechnicalParser (NOVO!)
                tech_redirects = row.get("redirects_found", [])
                if tech_redirects:
                    
                    # Se é string, tenta converter
                    if isinstance(tech_redirects, str):
                        try:
                            tech_redirects = json.loads(tech_redirects)
                        except:
                            tech_redirects = []
                    
                    # Converte formato TechnicalParser para formato LinksParser
                    if isinstance(tech_redirects, list):
                        for redirect in tech_redirects:
                            if isinstance(redirect, dict):
                                link_data = {
                                    'Type': 'Internal Link (Technical)',
                                    'From': redirect.get('source_url', row.get('url', '')),
                                    'To Original': redirect.get('link_url', ''),
                                    'To Final': redirect.get('final_url', ''),
                                    'Anchor': '',
                                    'Alt Text': '',
                                    'Follow': 'True',
                                    'Target': '',
                                    'Rel': '',
                                    'Status Code': str(redirect.get('status_code', '')),
                                    'Status': self._get_status_text(redirect.get('status_code', 0)),
                                    'Redirected': 'True',
                                    'Link Path': '',
                                    'Source': 'TechnicalParser'
                                }
                                all_redirected_links.append(link_data)

            if not all_redirected_links:
                self.logger.info("Nenhum redirect encontrado em nenhuma fonte (LinksParser + TechnicalParser)")
                return

            # Remove duplicatas e cria aba
            links_df = pd.DataFrame(all_redirected_links)
            links_df = links_df.drop_duplicates(subset=['From', 'To Original'], keep='first')

            # Garante colunas esperadas
            colunas = [
                'Type', 'From', 'To Original', 'To Final',
                'Anchor', 'Alt Text', 'Follow', 'Target', 'Rel',
                'Status Code', 'Status', 'Redirected', 'Link Path', 'Source'
            ]
            for col in colunas:
                if col not in links_df.columns:
                    links_df[col] = ''

            links_df = links_df[colunas]
            links_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            
            # Log sucesso
            sources = links_df['Source'].value_counts() if 'Source' in links_df.columns else {}
            self.logger.info(f"✅ Aba Internal criada com {len(links_df)} redirects de múltiplas fontes: {dict(sources)}")

        except Exception as e:
            self.logger.error(f"❌ Erro criando aba Internal: {e}")
            
            # Cria aba de erro
            error_df = pd.DataFrame([
                ['Erro criando aba Internal'],
                [f'Detalhes: {str(e)}'],
                ['Verifique se dados de redirect existem no DataFrame']
            ], columns=['Erro'])
            error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)

    def _get_status_text(self, status_code: int) -> str:  # ✅ CORRIGIDO: Dentro da classe
        """Helper para converter status codes"""
        return {
            200: 'OK', 301: 'Moved Permanently', 302: 'Found', 303: 'See Other',
            307: 'Temporary Redirect', 308: 'Permanent Redirect',
            404: 'Not Found', 403: 'Forbidden', 500: 'Internal Server Error', 0: 'Error'
        }.get(status_code, f'HTTP {status_code}')