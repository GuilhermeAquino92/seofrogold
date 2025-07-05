"""
seofrog/exporters/links_internos_redirect.py
Exportador da aba "links internos com redirect" estilo Screaming Frog
"""

import pandas as pd
from seofrog.core.export_interface import ExporterInterface

class InternalRedirectLinksExporter(ExporterInterface):
    def export(self, data: list, writer: pd.ExcelWriter):
        all_redirects = []

        for page in data:
            redirects = page.get('internal_redirects_details', [])
            for redirect in redirects:
                enriched = {
                    'URL de Origem': redirect.get('From'),
                    'Link Redirecionado': redirect.get('To (Original)'),
                    'URL Final': redirect.get('To (Final)'),
                    'Anchor Text': redirect.get('Anchor'),
                    'Código HTTP': redirect.get('Código'),
                    'Criticidade': redirect.get('Criticidade'),
                    'Sugestão': redirect.get('Sugestão')
                }
                all_redirects.append(enriched)

        if not all_redirects:
            self._create_success_sheet(writer, '✅ Todos os links internos apontam diretamente para o destino final!')
            return

        df = pd.DataFrame(all_redirects)
        df.drop_duplicates(inplace=True)
        df.sort_values(by=['Criticidade', 'Código HTTP'], ascending=[False, False], inplace=True)

        df.to_excel(writer, sheet_name='🔁 Links Internos Redirect', index=False)
