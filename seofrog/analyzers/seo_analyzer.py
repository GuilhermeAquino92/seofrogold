"""
seofrog/analyzers/seo_analyzer.py
SEO Analysis Module - Placeholder para implementação futura
"""

import pandas as pd
import os
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path

from seofrog.utils.logger import get_logger
from seofrog.core.exceptions import ExportException, ValidationException

def analyze_crawl_results(csv_file: str) -> Dict[str, Any]:
    """
    Analisa resultados de crawl do SEOFrog
    
    Args:
        csv_file: Caminho para arquivo CSV com resultados
        
    Returns:
        Dict com estatísticas e problemas encontrados
    """
    
    logger = get_logger('SEOAnalyzer')
    
    try:
        # Valida arquivo
        if not os.path.exists(csv_file):
            raise ValidationException(f"Arquivo não encontrado: {csv_file}")
        
        # Carrega dados
        logger.info(f"📊 Carregando dados de: {csv_file}")
        df = pd.read_csv(csv_file)
        
        if df.empty:
            raise ValidationException("Arquivo CSV está vazio")
        
        logger.info(f"📁 Carregadas {len(df)} URLs para análise")
        
        # === ANÁLISE BÁSICA ===
        analysis_results = {
            'file_info': {
                'filename': csv_file,
                'total_urls': len(df),
                'columns': list(df.columns),
                'filesize_mb': os.path.getsize(csv_file) / (1024 * 1024)
            }
        }
        
        # === STATUS CODES ===
        if 'status_code' in df.columns:
            status_analysis = analyze_status_codes(df)
            analysis_results['status_codes'] = status_analysis
        
        # === SEO ISSUES ===
        if all(col in df.columns for col in ['title', 'meta_description', 'h1_count']):
            seo_analysis = analyze_seo_issues(df)
            analysis_results['seo_issues'] = seo_analysis
        
        # === TECHNICAL ISSUES ===
        technical_analysis = analyze_technical_issues(df)
        analysis_results['technical_issues'] = technical_analysis
        
        # === PERFORMANCE STATS ===
        if 'response_time' in df.columns:
            performance_analysis = analyze_performance(df)
            analysis_results['performance'] = performance_analysis
        
        # === PRINT REPORT ===
        print_analysis_report(analysis_results)
        
        return analysis_results
        
    except Exception as e:
        logger.error(f"❌ Erro na análise: {e}")
        raise ExportException(f"Falha na análise do arquivo: {e}", filename=csv_file)

def analyze_status_codes(df: pd.DataFrame) -> Dict[str, Any]:
    """Analisa distribuição de status codes"""
    
    status_counts = df['status_code'].value_counts().to_dict()
    total_urls = len(df)
    
    return {
        'distribution': status_counts,
        'success_rate': len(df[df['status_code'] == 200]) / total_urls * 100,
        'error_count': len(df[df['status_code'] >= 400]),
        'redirect_count': len(df[(df['status_code'] >= 300) & (df['status_code'] < 400)]),
        'most_common': df['status_code'].mode().iloc[0] if len(df) > 0 else None
    }

def analyze_seo_issues(df: pd.DataFrame) -> Dict[str, Any]:
    """Analisa problemas SEO comuns"""
    
    issues = {}
    
    # === TITLES ===
    if 'title' in df.columns:
        title_issues = {
            'missing': len(df[df['title'].isna() | (df['title'] == '')]),
            'too_long': len(df[df['title_length'] > 60]) if 'title_length' in df.columns else 0,
            'too_short': len(df[df['title_length'] < 30]) if 'title_length' in df.columns else 0,
            'duplicates': len(df) - len(df['title'].drop_duplicates()) if not df['title'].isna().all() else 0
        }
        issues['titles'] = title_issues
    
    # === META DESCRIPTIONS ===
    if 'meta_description' in df.columns:
        meta_issues = {
            'missing': len(df[df['meta_description'].isna() | (df['meta_description'] == '')]),
            'too_long': len(df[df['meta_description_length'] > 160]) if 'meta_description_length' in df.columns else 0,
            'too_short': len(df[df['meta_description_length'] < 120]) if 'meta_description_length' in df.columns else 0,
            'duplicates': len(df) - len(df['meta_description'].drop_duplicates()) if not df['meta_description'].isna().all() else 0
        }
        issues['meta_descriptions'] = meta_issues
    
    # === H1s ===
    if 'h1_count' in df.columns:
        h1_issues = {
            'missing': len(df[df['h1_count'] == 0]),
            'multiple': len(df[df['h1_count'] > 1]),
            'with_h1': len(df[df['h1_count'] == 1])
        }
        issues['h1_tags'] = h1_issues
    
    # === IMAGES ===
    if 'images_without_alt' in df.columns:
        images_issues = {
            'total_images_without_alt': df['images_without_alt'].sum(),
            'pages_with_alt_issues': len(df[df['images_without_alt'] > 0])
        }
        issues['images'] = images_issues
    
    return issues

def analyze_technical_issues(df: pd.DataFrame) -> Dict[str, Any]:
    """Analisa problemas técnicos"""
    
    issues = {}
    
    # === CANONICAL URLs ===
    if 'canonical_url' in df.columns:
        canonical_issues = {
            'missing': len(df[df['canonical_url'].isna() | (df['canonical_url'] == '')]),
            'self_referencing': len(df[df['url'] == df['canonical_url']]) if 'url' in df.columns else 0
        }
        issues['canonical'] = canonical_issues
    
    # === CONTENT LENGTH ===
    if 'content_length' in df.columns:
        content_issues = {
            'empty_pages': len(df[df['content_length'] == 0]),
            'large_pages': len(df[df['content_length'] > 1024*1024]),  # > 1MB
            'avg_size_kb': df['content_length'].mean() / 1024 if len(df) > 0 else 0
        }
        issues['content'] = content_issues
    
    # === WORD COUNT ===
    if 'word_count' in df.columns:
        word_issues = {
            'thin_content': len(df[df['word_count'] < 300]),  # < 300 palavras
            'no_content': len(df[df['word_count'] == 0]),
            'avg_words': df['word_count'].mean() if len(df) > 0 else 0
        }
        issues['content_quality'] = word_issues
    
    return issues

def analyze_performance(df: pd.DataFrame) -> Dict[str, Any]:
    """Analisa performance das páginas"""
    
    response_times = df['response_time']
    
    return {
        'avg_response_time': response_times.mean(),
        'median_response_time': response_times.median(),
        'slow_pages': len(df[df['response_time'] > 3.0]),  # > 3 segundos
        'fast_pages': len(df[df['response_time'] < 1.0]),   # < 1 segundo
        'percentile_95': response_times.quantile(0.95),
        'max_response_time': response_times.max()
    }

def print_analysis_report(results: Dict[str, Any]):
    """Imprime relatório de análise formatado"""
    
    print("\n🔍 ===== RELATÓRIO DE ANÁLISE SEO =====")
    print("=" * 50)
    
    # === FILE INFO ===
    file_info = results.get('file_info', {})
    print(f"📁 Arquivo: {file_info.get('filename', 'N/A')}")
    print(f"📊 Total URLs: {file_info.get('total_urls', 0):,}")
    print(f"💽 Tamanho: {file_info.get('filesize_mb', 0):.1f} MB")
    
    # === STATUS CODES ===
    if 'status_codes' in results:
        status = results['status_codes']
        print(f"\n📈 STATUS CODES:")
        print(f"   ✅ Taxa de sucesso: {status.get('success_rate', 0):.1f}%")
        print(f"   ❌ Páginas com erro: {status.get('error_count', 0):,}")
        print(f"   🔄 Redirects: {status.get('redirect_count', 0):,}")
        
        distribution = status.get('distribution', {})
        for code, count in sorted(distribution.items())[:5]:  # Top 5
            print(f"      {code}: {count:,} URLs")
    
    # === SEO ISSUES ===
    if 'seo_issues' in results:
        seo = results['seo_issues']
        print(f"\n🎯 PROBLEMAS SEO:")
        
        if 'titles' in seo:
            titles = seo['titles']
            print(f"   📝 Títulos:")
            print(f"      Ausentes: {titles.get('missing', 0):,}")
            print(f"      Muito longos (>60): {titles.get('too_long', 0):,}")
            print(f"      Muito curtos (<30): {titles.get('too_short', 0):,}")
            print(f"      Duplicados: {titles.get('duplicates', 0):,}")
        
        if 'meta_descriptions' in seo:
            meta = seo['meta_descriptions']
            print(f"   📄 Meta Descriptions:")
            print(f"      Ausentes: {meta.get('missing', 0):,}")
            print(f"      Muito longas (>160): {meta.get('too_long', 0):,}")
            print(f"      Muito curtas (<120): {meta.get('too_short', 0):,}")
        
        if 'h1_tags' in seo:
            h1 = seo['h1_tags']
            print(f"   📑 Tags H1:")
            print(f"      Ausentes: {h1.get('missing', 0):,}")
            print(f"      Múltiplas: {h1.get('multiple', 0):,}")
        
        if 'images' in seo:
            img = seo['images']
            print(f"   🖼️  Imagens:")
            print(f"      Sem ALT text: {img.get('total_images_without_alt', 0):,}")
    
    # === PERFORMANCE ===
    if 'performance' in results:
        perf = results['performance']
        print(f"\n⚡ PERFORMANCE:")
        print(f"   Tempo médio: {perf.get('avg_response_time', 0):.2f}s")
        print(f"   Páginas lentas (>3s): {perf.get('slow_pages', 0):,}")
        print(f"   Páginas rápidas (<1s): {perf.get('fast_pages', 0):,}")
    
    print("\n" + "=" * 50)
    print("✅ Análise concluída!")

def analyze_cli():
    """Entry point para linha de comando de análise"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analisador de resultados SEOFrog')
    parser.add_argument('file', help='Arquivo CSV para analisar')
    
    args = parser.parse_args()
    
    try:
        analyze_crawl_results(args.file)
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    analyze_cli()