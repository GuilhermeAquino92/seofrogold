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

    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria aba "Internal" com apenas os links internos que redirecionam
        (ex: diferença de slug, capitalização, trailing slash, etc.)
        """
        try:
            all_redirected_links = []

            for row in df.to_dict(orient="records"):
                links = row.get("internal_links_details", [])
                if isinstance(links, str):
                    try:
                        links = json.loads(links)
                    except Exception as e:
                        self.logger.debug(f"Erro ao fazer json.loads nos links: {e}")
                        links = []

                # Filtra apenas links com Redirected == 'True'
                redirected_links = [link for link in links if str(link.get('Redirected', '')).lower() == 'true']
                all_redirected_links.extend(redirected_links)

            if not all_redirected_links:
                self.logger.info("Nenhum link com redirect desnecessário encontrado para a aba Internal")
                return

            links_df = pd.DataFrame(all_redirected_links)

            # Garante ordem de colunas esperada
            colunas = [
                'Type', 'From', 'To Original', 'To Final',
                'Anchor', 'Alt Text', 'Follow', 'Target', 'Rel',
                'Status Code', 'Status', 'Redirected', 'Link Path'
            ]
            for col in colunas:
                if col not in links_df.columns:
                    links_df[col] = ''

            links_df = links_df[colunas]
            links_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)

        except Exception as e:
            self.logger.error(f"Erro ao criar aba Internal: {e}")
            raise
