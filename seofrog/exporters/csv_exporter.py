"""
seofrog/exporters/csv_exporter.py
CSV Exporter Enterprise do SEOFrog v0.2
"""

import csv
import pandas as pd
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from seofrog.utils.logger import get_logger
from seofrog.core.exceptions import ExportException

class CSVExporter:
    """Exportador enterprise para CSV com colunas organizadas"""
    
    def __init__(self, output_dir: str = "seofrog_output"):
        self.output_dir = output_dir
        self.logger = get_logger('CSVExporter')
        
        # Cria diretório se não existir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    def export_results(self, crawl_data: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        Exporta dados do crawl para CSV com colunas organizadas
        
        Args:
            crawl_data: Lista de dicionários com dados do crawl
            filename: Nome do arquivo (opcional, gera automaticamente se None)
            
        Returns:
            Caminho do arquivo gerado
        """
        
        if not crawl_data:
            self.logger.warning("Nenhum dado para exportar")
            return ""
        
        # Gera filename se não fornecido
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"seofrog_crawl_{timestamp}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # Define ordem das colunas (as mais importantes primeiro)
            column_order = self._get_column_order()
            
            # Cria DataFrame
            df = pd.DataFrame(crawl_data)
            
            # Reordena colunas conforme importância
            available_columns = [col for col in column_order if col in df.columns]
            extra_columns = [col for col in df.columns if col not in column_order]
            final_columns = available_columns + sorted(extra_columns)
            
            # Aplica ordem final
            df = df[final_columns]
            
            # Preenche valores NaN
            df = df.fillna('')
            
            # Exporta para CSV
            df.to_csv(filepath, index=False, encoding='utf-8')
            
            # Log estatísticas
            total_rows = len(df)
            total_columns = len(df.columns)
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            
            self.logger.info(f"✅ CSV exportado: {filepath}")
            self.logger.info(f"📊 {total_rows:,} URLs × {total_columns} colunas ({file_size_mb:.1f} MB)")
            
            return filepath
            
        except Exception as e:
            error_msg = f"Erro exportando CSV: {e}"
            self.logger.error(error_msg)
            raise ExportException(error_msg, filename=filepath, format_type='csv')
    
    def _get_column_order(self) -> List[str]:
        """Define ordem das colunas por importância"""
        return [
            # === IDENTIFICAÇÃO ===
            'url',
            'final_url',
            'status_code',
            
            # === SEO BÁSICO ===
            'title',
            'title_length',
            'title_words',
            'meta_description',
            'meta_description_length',
            'meta_keywords',
            
            # === HEADINGS ===
            'h1_count',
            'h1_text',
            'h1_length',
            'h2_count',
            'h3_count',
            'h4_count',
            'h5_count',
            'h6_count',
            
            # === LINKS ===
            'internal_links_count',
            'external_links_count',
            'total_links_count',
            'links_without_anchor',
            
            # === IMAGES ===
            'images_count',
            'images_without_alt',
            'images_without_src',
            'images_with_dimensions',
            
            # === CONTENT ===
            'word_count',
            'character_count',
            'text_ratio',
            
            # === TECHNICAL ===
            'canonical_url',
            'canonical_is_self',
            'meta_robots',
            'meta_robots_noindex',
            'meta_robots_nofollow',
            'has_viewport',
            'viewport_content',
            'has_charset',
            'has_favicon',
            'is_amp',
            
            # === STRUCTURED DATA ===
            'schema_total_count',
            'schema_json_ld_count',
            'schema_microdata_count',
            'schema_rdfa_count',
            
            # === SOCIAL ===
            'og_tags_count',
            'og_title',
            'og_description',
            'twitter_tags_count',
            
            # === INTERNATIONAL ===
            'hreflang_count',
            'hreflang_languages',
            
            # === PERFORMANCE ===
            'response_time',
            'content_length',
            'content_type',
            'content_type_category',
            
            # === REDIRECTS ===
            'redirect_chain',
            'redirect_urls',
            
            # === METADATA ===
            'crawl_timestamp',
            'error',
            'parse_error'
        ]
    
    def export_summary_report(self, crawl_data: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        Exporta relatório resumido com estatísticas principais
        
        Args:
            crawl_data: Lista de dicionários com dados do crawl
            filename: Nome do arquivo (opcional)
            
        Returns:
            Caminho do arquivo gerado
        """
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"seofrog_summary_{timestamp}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            df = pd.DataFrame(crawl_data)
            
            # Cria resumo estatístico
            summary_data = []
            
            # === STATUS CODES ===
            if 'status_code' in df.columns:
                status_summary = df['status_code'].value_counts().to_dict()
                for status, count in status_summary.items():
                    summary_data.append({
                        'metric': f'Status Code {status}',
                        'count': count,
                        'percentage': round(count / len(df) * 100, 1)
                    })
            
            # === SEO ISSUES ===
            seo_metrics = {
                'URLs without title': len(df[df['title'] == '']) if 'title' in df.columns else 0,
                'URLs without meta description': len(df[df['meta_description'] == '']) if 'meta_description' in df.columns else 0,
                'URLs without H1': len(df[df['h1_count'] == 0]) if 'h1_count' in df.columns else 0,
                'URLs with multiple H1s': len(df[df['h1_count'] > 1]) if 'h1_count' in df.columns else 0,
                'Images without ALT': df['images_without_alt'].sum() if 'images_without_alt' in df.columns else 0,
            }
            
            for metric, count in seo_metrics.items():
                if isinstance(count, (int, float)) and len(df) > 0:
                    summary_data.append({
                        'metric': metric,
                        'count': count,
                        'percentage': round(count / len(df) * 100, 1) if 'URLs' in metric else count
                    })
            
            # === PERFORMANCE ===
            if 'response_time' in df.columns:
                response_times = df['response_time'].dropna()
                if len(response_times) > 0:
                    summary_data.extend([
                        {
                            'metric': 'Average Response Time (s)',
                            'count': round(response_times.mean(), 2),
                            'percentage': ''
                        },
                        {
                            'metric': 'Slow pages (>3s)',
                            'count': len(response_times[response_times > 3]),
                            'percentage': round(len(response_times[response_times > 3]) / len(response_times) * 100, 1)
                        }
                    ])
            
            # Exporta resumo
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_csv(filepath, index=False, encoding='utf-8')
            
            self.logger.info(f"📊 Relatório resumido exportado: {filepath}")
            return filepath
            
        except Exception as e:
            error_msg = f"Erro exportando resumo: {e}"
            self.logger.error(error_msg)
            raise ExportException(error_msg, filename=filepath, format_type='csv')
    
    def export_issues_only(self, crawl_data: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        Exporta apenas URLs com problemas SEO
        
        Args:
            crawl_data: Lista de dicionários com dados do crawl
            filename: Nome do arquivo (opcional)
            
        Returns:
            Caminho do arquivo gerado
        """
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"seofrog_issues_{timestamp}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            df = pd.DataFrame(crawl_data)
            
            # Filtra URLs com problemas
            issues_mask = (
                (df['status_code'] != 200) |  # Não é 200 OK
                (df['title'] == '') |  # Sem título
                (df['meta_description'] == '') |  # Sem meta description
                (df['h1_count'] == 0) |  # Sem H1
                (df['h1_count'] > 1) |  # Múltiplos H1s
                (df['canonical_url'] == '') |  # Sem canonical
                (df['images_without_alt'] > 0)  # Imagens sem ALT
            )
            
            issues_df = df[issues_mask].copy()
            
            # Adiciona coluna com tipos de problemas
            issues_df['issues_detected'] = issues_df.apply(self._detect_issues, axis=1)
            
            # Reordena colunas com issues_detected no início
            cols = ['url', 'status_code', 'issues_detected'] + [col for col in issues_df.columns if col not in ['url', 'status_code', 'issues_detected']]
            issues_df = issues_df[cols]
            
            # Exporta
            issues_df.to_csv(filepath, index=False, encoding='utf-8')
            
            self.logger.info(f"⚠️  Issues exportados: {filepath} ({len(issues_df):,} URLs com problemas)")
            return filepath
            
        except Exception as e:
            error_msg = f"Erro exportando issues: {e}"
            self.logger.error(error_msg)
            raise ExportException(error_msg, filename=filepath, format_type='csv')
    
    def _detect_issues(self, row) -> str:
        """Detecta tipos de problemas em uma linha"""
        issues = []
        
        if row.get('status_code', 200) != 200:
            issues.append(f"HTTP {row.get('status_code', 'Unknown')}")
        
        if row.get('title', '') == '':
            issues.append("No Title")
        
        if row.get('meta_description', '') == '':
            issues.append("No Meta Description")
        
        if row.get('h1_count', 1) == 0:
            issues.append("No H1")
        elif row.get('h1_count', 1) > 1:
            issues.append("Multiple H1s")
        
        if row.get('canonical_url', '') == '':
            issues.append("No Canonical")
        
        if row.get('images_without_alt', 0) > 0:
            issues.append(f"{row.get('images_without_alt', 0)} Images No ALT")
        
        if row.get('title_length', 0) > 60:
            issues.append("Title Too Long")
        elif row.get('title_length', 0) < 30 and row.get('title_length', 0) > 0:
            issues.append("Title Too Short")
        
        if row.get('meta_description_length', 0) > 160:
            issues.append("Meta Description Too Long")
        
        return "; ".join(issues) if issues else "No Issues"
    
    def export_issues_only(self, crawl_data: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        Exporta apenas URLs com problemas SEO
        """
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"seofrog_issues_{timestamp}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            df = pd.DataFrame(crawl_data)
            
            if df.empty:
                self.logger.warning("Nenhum dado para análise de issues")
                return ""
            
            # Verifica se colunas necessárias existem
            required_columns = ['url', 'status_code']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                self.logger.warning(f"Colunas necessárias ausentes: {missing_columns}")
                # Cria DataFrame básico apenas com URL e status
                basic_data = []
                for item in crawl_data:
                    basic_data.append({
                        'url': item.get('url', ''),
                        'status_code': item.get('status_code', 0),
                        'error': item.get('error', ''),
                        'issues_detected': 'Connection Failed' if item.get('status_code', 0) == 0 else 'Unknown'
                    })
                issues_df = pd.DataFrame(basic_data)
            else:
                # Filtra URLs com problemas (usa .get() para evitar KeyError)
                issues_mask = (
                    (df['status_code'] != 200) |  # Não é 200 OK
                    (df.get('title', '') == '') |  # Sem título
                    (df.get('meta_description', '') == '') |  # Sem meta description
                    (df.get('h1_count', 0) == 0) |  # Sem H1
                    (df.get('h1_count', 0) > 1) |  # Múltiplos H1s
                    (df.get('canonical_url', '') == '') |  # Sem canonical
                    (df.get('images_without_alt', 0) > 0)  # Imagens sem ALT
                )
                
                issues_df = df[issues_mask].copy()
                
                # Adiciona coluna com tipos de problemas
                issues_df['issues_detected'] = issues_df.apply(self._detect_issues, axis=1)
                
                # Reordena colunas com issues_detected no início
                cols = ['url', 'status_code', 'issues_detected'] + [col for col in issues_df.columns if col not in ['url', 'status_code', 'issues_detected']]
                issues_df = issues_df[cols]
            
            # Exporta
            issues_df.to_csv(filepath, index=False, encoding='utf-8')
            
            self.logger.info(f"⚠️  Issues exportados: {filepath} ({len(issues_df):,} URLs com problemas)")
            return filepath
            
        except Exception as e:
            error_msg = f"Erro exportando issues: {e}"
            self.logger.error(error_msg)
            raise ExportException(error_msg, filename=filepath, format_type='csv')