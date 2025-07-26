#!/usr/bin/env python3
"""
seofrog/cli.py
CLI Interface v0.2 - Integrado com Core Engine
"""

import argparse
import os
import sys
from typing import Dict, Any, Tuple, Optional
from urllib.parse import urlparse

# === IMPORTS INTERNOS ===
from seofrog.core.config import CrawlConfig, ProfileConfig, create_config_from_profile, create_auto_config
from seofrog.core.exceptions import ConfigException, ValidationException

# ==================== URL SANITIZER ====================

def sanitize_url(url: str) -> str:
    """Sanitiza e valida URL de entrada"""
    if not url:
        raise ValidationException("URL nao pode estar vazia")
    
    url = url.strip()
    
    # Remove caracteres invalidos comuns
    url = url.replace(' ', '%20')
    
    # Adiciona protocolo se nao existir
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Valida URL basica
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValidationException("URL invalida - dominio nao encontrado", field="url", value=url)
        
        # Valida caracteres no dominio
        domain = parsed.netloc.lower()
        if any(char in domain for char in ['<', '>', '"', '`', ' ']):
            raise ValidationException("Dominio contem caracteres invalidos", field="domain", value=domain)
        
        return url
    except Exception as e:
        if isinstance(e, ValidationException):
            raise
        raise ValidationException(f"URL invalida: {url}", field="url", value=url)

# ==================== CLI PARSER ====================

def create_cli_parser() -> argparse.ArgumentParser:
    """Cria parser CLI enterprise"""
    
    profiles = ProfileConfig.get_profiles()
    auto_workers = os.cpu_count() or 4
    
    parser = argparse.ArgumentParser(
        description=' SEOFrog v0.2 Enterprise - Professional Screaming Frog Clone',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
 EXEMPLOS DE USO:

 Crawl automatico (configuracao inteligente):
 seofrog exemplo.com
 seofrog https://loja.com
 seofrog blog.com.br

 Profiles pre-configurados:
 seofrog exemplo.com --profile quick # {profiles['quick'].description}
 seofrog exemplo.com --profile standard # {profiles['standard'].description}
 seofrog exemplo.com --profile deep # {profiles['deep'].description}
 seofrog exemplo.com --profile safe # {profiles['safe'].description}
 seofrog exemplo.com --profile enterprise # {profiles['enterprise'].description}

 Configuracao manual (sobrescreve profiles):
 seofrog exemplo.com --max-urls 50000 --workers 16 --delay 0.1
 seofrog exemplo.com --profile deep --max-urls 1000000
 seofrog exemplo.com --no-robots --crawl-images --crawl-css

 Analise de resultados:
 seofrog --analyze resultado.csv
 seofrog --analyze /path/to/crawl_data.csv

 CONFIGURACOES AUTO-DETECTADAS:
 CPU Cores: {auto_workers}
 Workers padrao: {auto_workers}
 Memoria recomendada: {auto_workers * 256}MB
 
 PROFILES DISPONIVEIS:
 Use --list-profiles para ver detalhes completos
 """
    )
    
    # ==================== ARGUMENTOS PRINCIPAIS ====================
    
    parser.add_argument('url', nargs='?', 
        help='URL inicial (adiciona https:// automaticamente se necessario)')
    
    # ==================== PROFILES ====================
    
    profile_group = parser.add_argument_group(' Profiles Pre-configurados')
    profile_group.add_argument('--profile', choices=list(profiles.keys()),
        help='Profile de crawl enterprise')
    profile_group.add_argument('--list-profiles', action='store_true',
        help='Lista todos os profiles disponiveis com detalhes')
    
    # ==================== CONFIGURACOES PRINCIPAIS ====================
    
    config_group = parser.add_argument_group(' Configuracoes de Crawl')
    config_group.add_argument('--max-urls', type=int,
        help='Maximo de URLs para crawlear')
    config_group.add_argument('--max-depth', type=int,
        help='Profundidade maxima do crawl')
    config_group.add_argument('--workers', type=int,
        help=f'Threads trabalhadoras (auto: {auto_workers})')
    config_group.add_argument('--delay', type=float,
        help='Delay entre requests em segundos')
    config_group.add_argument('--timeout', type=int,
        help='Timeout por request em segundos')
    
    # ==================== COMPORTAMENTO ====================
    
    behavior_group = parser.add_argument_group(' Comportamento')
    behavior_group.add_argument('--no-robots', action='store_true',
        help='Ignora robots.txt (nao recomendado)')
    behavior_group.add_argument('--no-redirects', action='store_true',
        help='Nao segue redirects')
    behavior_group.add_argument('--max-redirects', type=int,
        help='Maximo de redirects a seguir (padrao: 10)')
    
    # ==================== TIPOS DE CONTEUDO ====================
    
    content_group = parser.add_argument_group(' Tipos de Conteudo')
    content_group.add_argument('--crawl-images', action='store_true',
        help='Inclui imagens no crawl')
    content_group.add_argument('--crawl-css', action='store_true',
        help='Inclui arquivos CSS')
    content_group.add_argument('--crawl-js', action='store_true',
        help='Inclui arquivos JavaScript')
    content_group.add_argument('--crawl-pdf', action='store_true',
        help='Inclui arquivos PDF')
    
    # ==================== REDE E PERFORMANCE ====================
    
    network_group = parser.add_argument_group(' Rede e Performance')
    network_group.add_argument('--user-agent',
        help='User-Agent customizado')
    network_group.add_argument('--retry-attempts', type=int,
        help='Tentativas de retry por URL')
    network_group.add_argument('--memory-limit', type=int,
        help='Limite de memoria em MB')
    
    # ==================== OUTPUT ====================
    
    output_group = parser.add_argument_group(' Output e Export')
    output_group.add_argument('--output', 
        help='Diretorio de output')
    output_group.add_argument('--format', choices=['csv', 'xlsx'], 
        help=f'Formato de export (default: xlsx)')
    output_group.add_argument('--filename', 
        help='Nome do arquivo de output')
    output_group.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Nivel de logging')
    
    # ==================== UTILITARIOS ====================
    
    utils_group = parser.add_argument_group(' Utilitarios')
    utils_group.add_argument('--analyze', metavar='CSV_FILE',
        help='Analisa arquivo de crawl existente')
    utils_group.add_argument('--stats-only', action='store_true',
        help='Mostra apenas estatisticas, nao exporta arquivo')
    utils_group.add_argument('--version', action='version', version='SEOFrog v0.2.0')
    utils_group.add_argument('--dry-run', action='store_true',
        help='Simula execucao sem fazer crawl real')
    
    return parser

# ==================== CONFIG BUILDER ====================

def build_config_from_args(args) -> Dict[str, Any]:
    """Constroi configuracao final a partir dos argumentos CLI"""
    
    config_dict = {}
    
    # === APLICA PROFILE SE ESPECIFICADO ===
    if args.profile:
        try:
            profile_config = create_config_from_profile(args.profile)
            config_dict = profile_config.to_dict()
            print(f" Usando profile '{args.profile}': {ProfileConfig.get_profile(args.profile).description}")
        except ValueError as e:
            raise ConfigException(f"Profile invalido: {e}")
    else:
        # Usa configuracao automatica
        auto_config = create_auto_config()
        config_dict = auto_config.to_dict()
        print(f" Configuracao automatica: {auto_config.max_workers} workers, {auto_config.max_urls:,} URLs max")
    
    # === APLICA OVERRIDES DOS ARGUMENTOS ===
    
    # Mapeamento de argumentos CLI para config
    arg_mappings = {
        'max_urls': 'max_urls',
        'max_depth': 'max_depth', 
        'workers': 'max_workers',
        'delay': 'delay',
        'timeout': 'timeout',
        'max_redirects': 'max_redirects',
        'user_agent': 'user_agent',
        'retry_attempts': 'retry_attempts',
        'output': 'output_dir',
        'format': 'export_format',
        'log_level': 'log_level',
        'memory_limit': 'memory_limit_mb'
    }
    
    # Aplica overrides especificos
    for arg_name, config_key in arg_mappings.items():
        if hasattr(args, arg_name) and getattr(args, arg_name) is not None:
            config_dict[config_key] = getattr(args, arg_name)
    
    # === APLICA FLAGS BOOLEANAS ===
    
    if args.no_robots:
        config_dict['respect_robots'] = False
    if args.no_redirects:
        config_dict['follow_redirects'] = False
    if args.crawl_images:
        config_dict['crawl_images'] = True
    if args.crawl_css:
        config_dict['crawl_css'] = True
    if args.crawl_js:
        config_dict['crawl_js'] = True
    if args.crawl_pdf:
        config_dict['crawl_pdf'] = True
    
    return config_dict

# ==================== VALIDACOES ====================

def validate_final_config(config_dict: Dict[str, Any]) -> None:
    """Valida configuracao final antes de usar"""
    
    # Cria CrawlConfig temporario para validacao
    try:
        temp_config = CrawlConfig(**config_dict)
        temp_config.validate() # Usa validacao interna
    except (TypeError, ValueError) as e:
        raise ConfigException(f"Configuracao invalida: {e}")

# ==================== DISPLAY FUNCTIONS ====================

def show_profiles():
    """Mostra detalhes de todos os profiles"""
    profiles = ProfileConfig.get_profiles()
    
    print("\n PROFILES ENTERPRISE DISPONIVEIS:")
    print("=" * 60)
    
    for name, profile in profiles.items():
        config = profile.config
        print(f"\n {name.upper()}")
        print(f" {profile.description}")
        print(f" Max URLs: {config.max_urls:,}")
        print(f" Max Depth: {config.max_depth}")
        print(f" Workers: {config.max_workers}")
        print(f" Delay: {config.delay}s")
        print(f" Timeout: {config.timeout}s")
        print(f" Robots: {'Respeita' if config.respect_robots else 'Ignora'}")
        
        content_types = []
        if config.crawl_images: content_types.append('Images')
        if config.crawl_css: content_types.append('CSS')
        if config.crawl_js: content_types.append('JS')
        
        print(f" Conteudo: HTML" + (f" + {', '.join(content_types)}" if content_types else " apenas"))

def show_config_summary(url: str, config_dict: Dict[str, Any]):
    """Mostra resumo da configuracao enterprise"""
    print(f"\n SEOFrog v0.2 Enterprise - CONFIGURACAO ATIVA")
    print("=" * 60)
    print(f" URL de destino: {url}")
    print(f" Max URLs: {config_dict.get('max_urls', 'N/A'):,}")
    print(f" Max Depth: {config_dict.get('max_depth', 'N/A')}")
    print(f" Workers: {config_dict.get('max_workers', 'N/A')}")
    print(f" Delay: {config_dict.get('delay', 'N/A')}s")
    print(f" Timeout: {config_dict.get('timeout', 'N/A')}s")
    print(f" Max Redirects: {config_dict.get('max_redirects', 'N/A')}")
    print(f" Robots.txt: {'Respeita' if config_dict.get('respect_robots', True) else 'Ignora'}")
    print(f" Redirects: {'Segue' if config_dict.get('follow_redirects', True) else 'Bloqueia'}")
    print(f" Retry attempts: {config_dict.get('retry_attempts', 'N/A')}")
    
    # Tipos de conteudo
    crawl_types = []
    if config_dict.get('crawl_images'): crawl_types.append('Images')
    if config_dict.get('crawl_css'): crawl_types.append('CSS')
    if config_dict.get('crawl_js'): crawl_types.append('JS')
    if config_dict.get('crawl_pdf'): crawl_types.append('PDF')
    
    print(f" Tipos: HTML" + (f" + {', '.join(crawl_types)}" if crawl_types else " apenas"))
    print(f" Output: {config_dict.get('output_dir', 'N/A')}/")
    print(f" Log level: {config_dict.get('log_level', 'N/A')}")
    print(f" Formato: {config_dict.get('export_format', 'csv').upper()}")
    
    # Flags especiais
    flags = []
    if config_dict.get('stats_only'): flags.append('Stats Only')
    if config_dict.get('dry_run'): flags.append('Dry Run')
    if flags:
        print(f" Flags: {', '.join(flags)}")
    
    print("=" * 60)

# ==================== MAIN CLI FUNCTION ====================

def parse_cli_args() -> Tuple[Optional[str], Dict[str, Any]]:
    """Funcao principal do CLI - retorna URL e configuracao"""
    
    parser = create_cli_parser()
    args = parser.parse_args()
    
    # === UTILITARIOS QUE NAO PRECISAM DE URL ===
    
    if args.list_profiles:
        show_profiles()
        sys.exit(0)
    
    if args.analyze:
        return None, {'analyze_file': args.analyze}
    
    # === VALIDA URL OBRIGATORIA PARA CRAWL ===
    
    if not args.url:
        parser.error("URL e obrigatoria para crawling. Use --help para exemplos ou --analyze para analisar arquivo existente.")
    
    # === SANITIZA E VALIDA URL ===
    
    try:
        url = sanitize_url(args.url)
    except ValidationException as e:
        parser.error(f"Erro na URL: {e.message}")
    
    # === CONSTROI CONFIGURACAO ===
    
    try:
        config_dict = build_config_from_args(args)
        validate_final_config(config_dict)
    except (ConfigException, ValidationException) as e:
        parser.error(f"Erro na configuracao: {e.message}")
    
    # === ADICIONA FLAGS ESPECIAIS ===
    
    config_dict['stats_only'] = args.stats_only
    config_dict['dry_run'] = args.dry_run
    config_dict['filename'] = args.filename
    
    # === MOSTRA RESUMO DA CONFIGURACAO ===
    
    if not args.dry_run: # Nao mostra resumo no dry-run
        show_config_summary(url, config_dict)
    
    return url, config_dict

# ==================== INTEGRATION HELPER ====================

def get_config_for_seofrog(config_dict: Dict[str, Any]) -> CrawlConfig:
    """Converte dict de config para CrawlConfig dataclass"""
    
    try:
        # Remove argumentos que nao sao parte do CrawlConfig
        crawl_config_keys = {
            'max_urls', 'max_depth', 'delay', 'timeout', 'max_workers', 'max_redirects',
            'respect_robots', 'follow_redirects', 'crawl_images', 'crawl_css', 'crawl_js', 'crawl_pdf',
            'user_agent', 'retry_attempts', 'retry_backoff', 'connection_pool_size',
            'output_dir', 'log_level', 'export_format', 'memory_limit_mb', 'enable_compression',
            'chunk_size', 'custom_headers', 'ignore_extensions'
        }
        
        # Filtra apenas as chaves validas para CrawlConfig
        filtered_config = {k: v for k, v in config_dict.items() if k in crawl_config_keys}
        
        return CrawlConfig(**filtered_config)
    except (TypeError, ValueError) as e:
        raise ConfigException(f"Erro criando CrawlConfig: {e}")

# ==================== STANDALONE TESTING ====================

if __name__ == "__main__":
    """Teste standalone do CLI"""
    try:
        url, config = parse_cli_args()
        
        if config.get('analyze_file'):
            print(f" Modo analise: {config['analyze_file']}")
        else:
            print(f" Modo crawl: {url}")
            print(f" Config final: {len(config)} parametros configurados")
        
        # Testa conversao para CrawlConfig
        crawl_config = get_config_for_seofrog(config)
        print(f" CrawlConfig criado com sucesso: {crawl_config.max_workers} workers")
        
    except Exception as e:
        print(f" Erro no teste: {e}")
        sys.exit(1)