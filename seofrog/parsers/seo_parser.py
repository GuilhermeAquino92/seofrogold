"""
PATCH 2: seofrog/parsers/seo_parser.py
Corrige como os dados de redirects são passados para o DataFrame
"""

# ✅ Encontre esta seção no seo_parser.py e substitua:

# ANTES (PROBLEMÁTICO):
# data['internal_redirects_details'] = self.links_parser.internal_redirect_links

# DEPOIS (CORRETO):
def parse_url_data(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    """
    Parse completo de uma URL com todos os parsers modulares
    ✅ CORRIGIDO: Dados de redirects específicos por URL
    """
    data = {'url': url}
    
    try:
        # ... outros parsers ...
        
        # 7. LINKS PARSER (com correção)
        try:
            word_count = data.get('word_count')
            links_data = self.links_parser.parse(soup, url, word_count)
            data.update(links_data)
            self.logger.debug(f"✅ LinksParser: {len(links_data)} campos")

            # ✅ CORREÇÃO PRINCIPAL: Dados específicos desta URL
            redirects_for_this_url = self.links_parser.get_redirects_for_url(url)
            
            if redirects_for_this_url:
                # Converte estrutura normalizada para formato legado (compatibilidade)
                legacy_format = []
                for redirect in redirects_for_this_url:
                    legacy_item = {
                        'From': redirect.get('from_url', ''),
                        'To (Original)': redirect.get('to_original', ''),
                        'To (Final)': redirect.get('to_final', ''),
                        'Anchor': redirect.get('anchor_text', ''),
                        'Alt Text': redirect.get('alt_text', ''),
                        'Follow': 'True' if redirect.get('follow', True) else 'False',
                        'Target': redirect.get('target', ''),
                        'Rel': redirect.get('rel', ''),
                        'Código': redirect.get('status_code', ''),
                        'Criticidade': redirect.get('criticidade', ''),
                        'Sugestão': redirect.get('sugestao', ''),
                        'Link Path': redirect.get('link_path', '')
                    }
                    legacy_format.append(legacy_item)
                
                data['internal_redirects_details'] = legacy_format
                self.logger.debug(f"✅ {len(legacy_format)} redirects específicos para {url}")
            else:
                data['internal_redirects_details'] = []
                
            # ✅ NOVO: Estatísticas gerais de redirects
            total_redirects = self.links_parser.get_total_redirects_count()
            data['total_redirects_found'] = total_redirects
            
        except Exception as e:
            self.logger.error(f"❌ LinksParser falhou: {e}")
            data['links_parser_error'] = str(e)
            data['internal_redirects_details'] = []  # ✅ Fallback seguro
        
        # ... resto do código ...
        
        # ✅ Log final com estatísticas
        total_fields = len(data)
        errors = len([k for k in data.keys() if k.endswith('_parser_error')])
        redirects_count = len(data.get('internal_redirects_details', []))
        
        self.logger.info(f"🌟 Parsing completo: {total_fields} campos, {redirects_count} redirects")
        if errors > 0:
            self.logger.warning(f"⚠️ {errors} parsers com erro")

        return data

    except Exception as e:
        self.logger.error(f"❌ Erro crítico no parsing de {url}: {e}")
        data['parse_error'] = str(e)
        data['internal_redirects_details'] = []  # ✅ Fallback seguro
        return data

# ✅ NOVO: Método para log final do crawl
def finalize_parsing(self):
    """
    Finaliza parsing e exibe resumo dos redirects encontrados
    """
    if hasattr(self, 'links_parser') and self.links_parser:
        self.links_parser.log_redirect_summary()