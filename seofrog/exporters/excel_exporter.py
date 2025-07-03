"""
seofrog/exporters/excel_exporter.py
Excel Exporter Enterprise do SEOFrog v0.2 - VERSÃO COMPLETA COM REDIRECTS
Usa todas as 13 sheets especializadas + nova aba de redirects
"""

import pandas as pd
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from urllib.parse import urlparse

# Imports de dependências opcionais
try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

from seofrog.utils.logger import get_logger
from seofrog.core.exceptions import ExportException
from .excel_writer import ExcelWriter

# Imports de todas as sheets modulares
from .sheets.dados_completos import DadosCompletosSheet
from .sheets.resumo_executivo import ResumoExecutivoSheet
from .sheets.erros_http import ErrosHttpSheet
from .sheets.problemas_titulos import ProblemasTitulosSheet
from .sheets.problemas_meta import ProblemasMetaSheet
from .sheets.problemas_headings import ProblemasHeadingsSheet
from .sheets.h1_h2_ausentes import H1H2AusentesSheet
from .sheets.problemas_imagens import ProblemasImagensSheet
from .sheets.problemas_tecnicos import ProblemasTecnicosSheet
from .sheets.problemas_performance import ProblemasPerformanceSheet
from .sheets.mixed_content import MixedContentSheet
from .sheets.analise_tecnica import AnaliseTecnicaSheet
# 🆕 NOVA SHEET DE LINKS COM REDIRECTS
from .sheets.links_internos_redirect import LinksInternosRedirectSheet

class ExcelExporter:
    """
    Exportador Excel Enterprise - VERSÃO MODULAR COMPLETA COM REDIRECTS
    Usa arquitetura modular com 13 sheets especializadas (incluindo redirects)
    """
    
    def __init__(self, output_dir: str = "seofrog_output"):
        self.output_dir = output_dir
        self.logger = get_logger('ExcelExporter')
        self.writer = ExcelWriter()
        
        # Cria diretório se não existir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Verifica dependências
        if not OPENPYXL_AVAILABLE:
            self.logger.warning("openpyxl não disponível. Install: pip install openpyxl")
        
        # Define ordem das sheets (incluindo nova aba de redirects)
        self.ALL_SHEETS = [
            DadosCompletosSheet,        # 1. Dados principais
            ResumoExecutivoSheet,       # 2. KPIs e estatísticas
            ErrosHttpSheet,             # 3. Status HTTP != 200
            ProblemasTitulosSheet,      # 4. Títulos problemáticos  
            ProblemasMetaSheet,         # 5. Meta descriptions problemáticas
            ProblemasHeadingsSheet,     # 6. Problemas de headings gerais
            H1H2AusentesSheet,          # 7. H1/H2 ausentes (crítico)
            ProblemasImagensSheet,      # 8. Imagens sem ALT/SRC
            ProblemasTecnicosSheet,     # 9. Canonical, viewport, charset
            ProblemasPerformanceSheet,  # 10. Páginas lentas/pesadas
            MixedContentSheet,          # 11. Problemas HTTPS/HTTP
            LinksInternosRedirectSheet, # 12. 🆕 Links com redirects
            AnaliseTecnicaSheet,        # 13. Análise técnica final
        ]
    
    def export_results(self, crawl_data: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        Exporta dados para Excel usando arquitetura modular completa
        
        Args:
            crawl_data: Lista de dicionários com dados crawleados
            filename: Nome do arquivo (opcional)
            
        Returns:
            str: Caminho do arquivo gerado
        """
        try:
            if not crawl_data:
                raise ExportException("Nenhum dado para exportar")
            
            # Gera filename se não fornecido
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"seofrog_crawl_{timestamp}.xlsx"
            
            filepath = os.path.join(self.output_dir, filename)
            
            # Converte para DataFrame
            df = pd.DataFrame(crawl_data)
            if df.empty:
                raise ExportException("DataFrame vazio após conversão")
            
            # Log início do processo
            self.logger.info(f"🚀 Iniciando export modular: {len(df)} URLs")
            
            # Exporta usando arquitetura modular
            engine = 'openpyxl' if OPENPYXL_AVAILABLE else 'xlsxwriter'
            with pd.ExcelWriter(filepath, engine=engine) as writer:
                
                # === CRIA TODAS AS SHEETS MODULARES ===
                self._create_all_modular_sheets(df, writer)
                
                # === NOVA ABA DE REDIRECTS ===
                self._create_redirects_sheet(writer, df)
                
                # === FORMATAÇÃO ===
                if OPENPYXL_AVAILABLE:
                    self.writer.format_workbook(writer)
            
            # Log estatísticas finais
            self._log_export_stats(df, filepath)
            return filepath
            
        except Exception as e:
            error_msg = f"Erro no export modular: {e}"
            self.logger.error(error_msg)
            raise ExportException(error_msg)
    
    def _create_all_modular_sheets(self, df: pd.DataFrame, writer):
        """
        Cria todas as sheets usando arquitetura modular
        """
        self.logger.info(f"📊 Criando {len(self.ALL_SHEETS)} sheets modulares...")
        
        sheets_created = 0
        sheets_failed = 0
        
        for i, sheet_class in enumerate(self.ALL_SHEETS, 1):
            try:
                # Instancia a sheet
                sheet_instance = sheet_class()
                sheet_name = sheet_instance.get_sheet_name()
                
                # Cria a sheet
                sheet_instance.create_sheet(df, writer)
                
                sheets_created += 1
                self.logger.debug(f"✅ [{i:2d}/13] {sheet_name}")
                
            except Exception as e:
                sheets_failed += 1
                sheet_name = getattr(sheet_class, '__name__', 'Unknown')
                self.logger.error(f"❌ [{i:2d}/13] {sheet_name}: {e}")
                
                # Cria sheet de erro como fallback
                try:
                    error_df = pd.DataFrame([[f'Erro criando {sheet_name}: {str(e)}']], columns=['Erro'])
                    error_df.to_excel(writer, sheet_name=f'Erro_{i}', index=False)
                except:
                    pass  # Se nem o fallback funcionar, continua
        
        # Log final
        if sheets_failed == 0:
            self.logger.info(f"🎉 Todas as {sheets_created} sheets criadas com sucesso!")
        else:
            self.logger.warning(f"⚠️ {sheets_created} sheets criadas, {sheets_failed} falharam")
    
    # ==========================================
    # NOVA FUNCIONALIDADE: ANÁLISE DE REDIRECTS
    # ==========================================
    
    def _create_redirects_sheet(self, writer, df: pd.DataFrame):
        """
        Cria aba de análise de redirects - NOVA FUNCIONALIDADE
        
        Args:
            writer: pd.ExcelWriter object
            df: DataFrame com dados do crawl
        """
        try:
            # Analisa problemas de redirect
            redirect_issues = self._analyze_redirect_issues(df)
            
            if redirect_issues:
                # Cria DataFrame
                redirects_df = pd.DataFrame(redirect_issues)
                
                # Ordena por criticidade
                priority_order = {'CRÍTICO': 1, 'ALTO': 2, 'MÉDIO': 3, 'BAIXO': 4}
                redirects_df['_priority'] = redirects_df['criticidade'].map(priority_order).fillna(4)
                redirects_df = redirects_df.sort_values(['_priority', 'url_original']).drop('_priority', axis=1)
                
                # Exporta para Excel
                redirects_df.to_excel(writer, sheet_name='🔄 Redirects Detectados', index=False)
                
                self.logger.info(f"✅ Aba Redirects: {len(redirects_df)} problemas encontrados")
                
                # Estatísticas de redirects
                self._log_redirect_stats(redirects_df)
                
            else:
                # Nenhum problema encontrado
                success_df = pd.DataFrame([
                    ['✅ Nenhum redirect problemático detectado!'],
                    ['🎯 Todas as URLs redirecionam corretamente'],
                    ['📋 Verifique se há redirects no crawl']
                ], columns=['Status'])
                success_df.to_excel(writer, sheet_name='🔄 Redirects Detectados', index=False)
                self.logger.info("✅ Aba Redirects: Nenhum problema encontrado")
                
        except Exception as e:
            self.logger.error(f"Erro criando aba de redirects: {e}")
            error_df = pd.DataFrame([[f'Erro na análise de redirects: {str(e)}']], columns=['Erro'])
            error_df.to_excel(writer, sheet_name='🔄 Redirects Detectados', index=False)
    
    def _analyze_redirect_issues(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Analisa problemas de redirect baseado nos dados crawleados
        
        Args:
            df: DataFrame com dados do crawl
            
        Returns:
            Lista de dicionários com problemas detectados
        """
        redirect_issues = []
        
        for _, row in df.iterrows():
            url = row.get('url', '')
            final_url = row.get('final_url', '')
            status_code = row.get('status_code', 200)
            response_time = row.get('response_time', 0)
            title = row.get('title', '')
            
            # Detecta redirects básicos (URL original != final)
            if url != final_url and url and final_url:
                issue_type, criticality = self._classify_redirect(url, final_url, status_code)
                
                redirect_issues.append({
                    'url_original': url,
                    'url_final': final_url,
                    'codigo_redirect': status_code,
                    'tipo_problema': issue_type,
                    'criticidade': criticality,
                    'titulo_pagina': title[:50] + '...' if len(title) > 50 else title,
                    'tempo_resposta': f"{response_time:.3f}s" if response_time > 0 else '',
                    'solucao': self._get_redirect_solution(issue_type),
                    'impacto_seo': self._get_redirect_impact(issue_type),
                    'prioridade_correcao': self._get_correction_priority(criticality, issue_type)
                })
            
            # Detecta outros problemas relacionados a redirects
            elif status_code in [301, 302, 303, 307, 308] and url == final_url:
                # Redirect que não mudou a URL (possível problema de configuração)
                redirect_issues.append({
                    'url_original': url,
                    'url_final': final_url,
                    'codigo_redirect': status_code,
                    'tipo_problema': 'Redirect sem mudança de URL',
                    'criticidade': 'MÉDIO',
                    'titulo_pagina': title[:50] + '...' if len(title) > 50 else title,
                    'tempo_resposta': f"{response_time:.3f}s" if response_time > 0 else '',
                    'solucao': 'Verificar configuração do servidor',
                    'impacto_seo': 'Possible redirect loop ou configuração incorreta',
                    'prioridade_correcao': 'Investigar servidor'
                })
        
        return redirect_issues
    
    def _classify_redirect(self, original_url: str, final_url: str, status_code: int) -> tuple:
        """
        Classifica o tipo de redirect e sua criticidade
        
        Args:
            original_url: URL original
            final_url: URL final
            status_code: Código de status HTTP
            
        Returns:
            tuple: (tipo_problema, criticidade)
        """
        try:
            orig_parsed = urlparse(original_url)
            final_parsed = urlparse(final_url)
            
            # HTTP -> HTTPS (crítico para SEO)
            if orig_parsed.scheme == 'http' and final_parsed.scheme == 'https':
                return 'HTTP → HTTPS', 'ALTO'
            
            # HTTPS -> HTTP (muito problemático)
            if orig_parsed.scheme == 'https' and final_parsed.scheme == 'http':
                return 'HTTPS → HTTP (Crítico!)', 'CRÍTICO'
            
            # Mudança de domínio
            if orig_parsed.netloc != final_parsed.netloc:
                return 'Mudança de Domínio', 'ALTO'
            
            # WWW redirect
            if 'www.' in orig_parsed.netloc != 'www.' in final_parsed.netloc:
                return 'WWW Redirect', 'MÉDIO'
            
            # Trailing slash
            if orig_parsed.path.rstrip('/') == final_parsed.path.rstrip('/'):
                return 'Trailing Slash', 'BAIXO'
            
            # Capitalização
            if orig_parsed.path.lower() == final_parsed.path.lower() and orig_parsed.path != final_parsed.path:
                return 'Capitalização', 'MÉDIO'
            
            # Query string redirect
            if orig_parsed.path == final_parsed.path and orig_parsed.query != final_parsed.query:
                return 'Query String', 'BAIXO'
            
            # Path change
            if orig_parsed.netloc == final_parsed.netloc and orig_parsed.path != final_parsed.path:
                return 'Mudança de Path', 'MÉDIO'
            
            # Tipo genérico baseado no status code
            if status_code == 301:
                return 'Redirect Permanente', 'MÉDIO'
            elif status_code == 302:
                return 'Redirect Temporário', 'BAIXO'
            else:
                return f'Redirect {status_code}', 'BAIXO'
                
        except Exception:
            return 'Redirect Detectado', 'BAIXO'
    
    def _get_redirect_solution(self, issue_type: str) -> str:
        """
        Retorna solução específica para cada tipo de problema
        
        Args:
            issue_type: Tipo do problema detectado
            
        Returns:
            str: Sugestão de solução
        """
        solutions = {
            'HTTP → HTTPS': 'Atualizar todas as URLs internas para HTTPS',
            'HTTPS → HTTP (Crítico!)': 'URGENTE: Corrigir configuração - manter HTTPS',
            'Mudança de Domínio': 'Verificar se mudança é intencional',
            'WWW Redirect': 'Padronizar uso de www em links internos',
            'Trailing Slash': 'Padronizar links com ou sem trailing slash',
            'Capitalização': 'Corrigir capitalização nos links internos',
            'Query String': 'Remover query strings desnecessárias',
            'Mudança de Path': 'Atualizar URLs para nova estrutura',
            'Redirect Permanente': 'Atualizar links para URL final',
            'Redirect Temporário': 'Verificar se redirect ainda é necessário',
            'Redirect sem mudança de URL': 'Verificar configuração do servidor'
        }
        return solutions.get(issue_type, 'Investigar e corrigir redirect')
    
    def _get_redirect_impact(self, issue_type: str) -> str:
        """
        Descreve o impacto SEO de cada tipo de problema
        
        Args:
            issue_type: Tipo do problema
            
        Returns:
            str: Descrição do impacto
        """
        impacts = {
            'HTTP → HTTPS': 'Perda de link juice + problemas de segurança',
            'HTTPS → HTTP (Crítico!)': 'CRÍTICO: Perda de segurança + penalização SEO',
            'Mudança de Domínio': 'Possível perda de autoridade se não intencional',
            'WWW Redirect': 'Diluição de autoridade + crawl budget',
            'Trailing Slash': 'Redirect desnecessário + inconsistência',
            'Capitalização': 'Diluição de autoridade + problemas de indexação',
            'Query String': 'Crawl budget + possível duplicate content',
            'Mudança de Path': 'Perda de link juice + crawl budget',
            'Redirect Permanente': 'Crawl budget + delay de indexação',
            'Redirect Temporário': 'Não passa autoridade completa',
            'Redirect sem mudança de URL': 'Crawl budget + possível loop'
        }
        return impacts.get(issue_type, 'Redirect desnecessário + crawl budget')
    
    def _get_correction_priority(self, criticality: str, issue_type: str) -> str:
        """
        Define prioridade de correção
        
        Args:
            criticality: Nível de criticidade
            issue_type: Tipo do problema
            
        Returns:
            str: Prioridade de correção
        """
        if criticality == 'CRÍTICO':
            return '🚨 URGENTE - Corrigir imediatamente'
        elif criticality == 'ALTO':
            return '🔥 ALTA - Corrigir esta semana'
        elif criticality == 'MÉDIO':
            return '⚠️ MÉDIA - Corrigir este mês'
        else:
            return '📝 BAIXA - Incluir em próxima manutenção'
    
    def _log_redirect_stats(self, redirects_df: pd.DataFrame):
        """
        Loga estatísticas de redirects
        
        Args:
            redirects_df: DataFrame com problemas de redirect
        """
        try:
            total_redirects = len(redirects_df)
            critical_redirects = len(redirects_df[redirects_df['criticidade'] == 'CRÍTICO'])
            high_redirects = len(redirects_df[redirects_df['criticidade'] == 'ALTO'])
            
            self.logger.info(f"🔄 Redirects detectados: {total_redirects} total")
            if critical_redirects > 0:
                self.logger.info(f"🚨 {critical_redirects} redirects CRÍTICOS necessitam ação imediata")
            if high_redirects > 0:
                self.logger.info(f"🔥 {high_redirects} redirects de ALTA prioridade")
            
            # Top tipos de problemas
            top_types = redirects_df['tipo_problema'].value_counts().head(3)
            self.logger.info(f"📊 Principais problemas: {dict(top_types)}")
            
        except Exception as e:
            self.logger.debug(f"Erro calculando estatísticas de redirect: {e}")
    
    # ==========================================
    # MÉTODOS EXISTENTES (MANTIDOS)
    # ==========================================
    
    def _log_export_stats(self, df: pd.DataFrame, filepath: str):
        """
        Loga estatísticas detalhadas do export
        """
        total_rows = len(df)
        total_columns = len(df.columns)
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        
        self.logger.info(f"✅ Excel modular exportado: {filepath}")
        self.logger.info(f"📊 {total_rows:,} URLs × {total_columns} colunas ({file_size_mb:.1f} MB)")
        self.logger.info(f"🗂️ {len(self.ALL_SHEETS)} sheets especializadas + aba de redirects")
        
        # Estatísticas por categoria
        self._log_category_stats(df)
    
    def _log_category_stats(self, df: pd.DataFrame):
        """
        Loga estatísticas por categoria de problemas
        """
        try:
            total_urls = len(df)
            
            # Status codes
            if 'status_code' in df.columns:
                errors = len(df[df['status_code'] != 200])
                if errors > 0:
                    self.logger.info(f"🚨 {errors} URLs com erros HTTP ({errors/total_urls*100:.1f}%)")
            
            # Redirects detectados
            redirects_detected = len(df[df['url'] != df['final_url']])
            if redirects_detected > 0:
                self.logger.info(f"🔄 {redirects_detected} redirects detectados ({redirects_detected/total_urls*100:.1f}%)")
            
            # SEO crítico
            if 'title' in df.columns:
                no_titles = len(df[df['title'].fillna('') == ''])
                if no_titles > 0:
                    self.logger.info(f"📝 {no_titles} URLs sem título ({no_titles/total_urls*100:.1f}%)")
            
            if 'h1_count' in df.columns:
                no_h1 = len(df[df['h1_count'].fillna(0) == 0])
                if no_h1 > 0:
                    self.logger.info(f"🚨 {no_h1} URLs sem H1 ({no_h1/total_urls*100:.1f}%)")
            
            # Performance
            if 'response_time' in df.columns:
                slow_pages = len(df[df['response_time'].fillna(0) > 3])
                if slow_pages > 0:
                    self.logger.info(f"⚡ {slow_pages} páginas lentas ({slow_pages/total_urls*100:.1f}%)")
            
            # Mixed Content
            if 'total_mixed_content_count' in df.columns:
                mixed_content = len(df[df['total_mixed_content_count'].fillna(0) > 0])
                if mixed_content > 0:
                    self.logger.info(f"🔒 {mixed_content} URLs com Mixed Content ({mixed_content/total_urls*100:.1f}%)")
            
        except Exception as e:
            self.logger.debug(f"Erro calculando estatísticas: {e}")


# ==========================================
# FUNÇÃO AUXILIAR PARA USO EXTERNO
# ==========================================

def export_to_excel(crawl_data: List[Dict[str, Any]], 
                   output_dir: str = "seofrog_output", 
                   filename: Optional[str] = None) -> str:
    """
    Função auxiliar para exportar dados para Excel usando arquitetura modular
    
    Args:
        crawl_data: Lista de dicionários com dados do crawl
        output_dir: Diretório de saída
        filename: Nome do arquivo (opcional)
    
    Returns:
        Caminho do arquivo gerado
        
    Example:
        >>> data = [{'url': 'example.com', 'title': 'Test', 'status_code': 200}]
        >>> filepath = export_to_excel(data)
        >>> print(f"Excel gerado: {filepath}")
    """
    exporter = ExcelExporter(output_dir)
    return exporter.export_results(crawl_data, filename)


# ==========================================
# COMPATIBILIDADE COM VERSÃO ANTERIOR
# ==========================================

# Para manter compatibilidade com código existente que espera métodos específicos
class LegacyExcelExporter(ExcelExporter):
    """
    Wrapper para compatibilidade com versão anterior
    Mantém interface antiga mas usa arquitetura modular internamente
    """
    
    def export_data(self, data: List[Dict], domain: str, format_type: str = 'xlsx') -> str:
        """Método legacy - redireciona para nova arquitetura"""
        if format_type.lower() != 'xlsx':
            raise ValueError("LegacyExcelExporter só suporta formato xlsx")
        
        filename = f"seofrog_{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return self.export_results(data, filename)