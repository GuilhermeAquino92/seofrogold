"""
SEOFrog v0.2 Enterprise
Professional Screaming Frog Clone - Enterprise-grade web crawler for SEO analysis

Copyright (c) 2024 SEOFrog Team
Licensed under MIT License
"""

__version__ = "0.2.0"
__author__ = "SEOFrog Team"
__email__ = "dev@seofrog.com"
__description__ = "Professional Screaming Frog Clone - Enterprise SEO Crawler"
__url__ = "https://github.com/seofrog/seofrog"

# === CORE EXPORTS ===
from seofrog.core.config import CrawlConfig, ProfileConfig
from seofrog.core.exceptions import (
    SEOFrogException, ConfigException, CrawlException,
    NetworkException, ParseException, ExportException, ValidationException
)
from seofrog.utils.logger import setup_logging, get_logger


# === FUTURE EXPORTS (quando implementados) ===
# from seofrog.core.crawler import SEOFrog
# from seofrog.analyzers.seo_analyzer import analyze_crawl_results

# === PACKAGE INFO ===
__all__ = [
    # Version info
    '__version__',
    '__author__',
    '__email__',
    '__description__',
    '__url__',
    
    # Core classes
    'CrawlConfig',
    'ProfileConfig',
    
    # Exceptions
    'SEOFrogException',
    'ConfigException', 
    'CrawlException',
    'NetworkException',
    'ParseException',
    'ExportException',
    'ValidationException',
    
    # Utils
    'setup_logging',
    'get_logger',
    
    # Future exports
    # 'SEOFrog',
    # 'analyze_crawl_results',
]

# === PACKAGE VALIDATION ===
def validate_environment():
    """Valida ambiente e dependências"""
    import sys
    import platform
    
    # Python version check
    if sys.version_info < (3, 9):
        raise RuntimeError(f"SEOFrog requires Python 3.9+, got {sys.version}")
    
    # Check critical dependencies
    required_packages = [
        'requests', 'beautifulsoup4', 'lxml', 'pandas', 'urllib3'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        raise RuntimeError(f"Missing required packages: {', '.join(missing_packages)}")

# === PACKAGE INITIALIZATION ===
try:
    validate_environment()
except RuntimeError as e:
    import warnings
    warnings.warn(f"SEOFrog initialization warning: {e}", RuntimeWarning)

# === CONVENIENCE FUNCTIONS ===

def get_version_info():
    """Retorna informações detalhadas da versão"""
    import sys
    import platform
    
    return {
        'seofrog_version': __version__,
        'python_version': sys.version,
        'platform': platform.platform(),
        'architecture': platform.architecture()[0],
    }

def quick_crawl(url: str, max_urls: int = 100, profile: str = 'quick') -> dict:
    """
    Função de conveniência para crawl rápido
    
    Args:
        url: URL para crawlear
        max_urls: Máximo de URLs
        profile: Profile a usar
    
    Returns:
        Dicionário com resultados do crawl
    
    Example:
        >>> from seofrog import quick_crawl
        >>> results = quick_crawl('https://example.com', max_urls=50)
    """
    
    # TODO: Implementar quando SEOFrog core estiver pronto
    raise NotImplementedError("quick_crawl será implementado quando SEOFrog core estiver disponível")

def create_config(profile: str = 'standard', **kwargs) -> CrawlConfig:
    """
    Função de conveniência para criar configuração
    
    Args:
        profile: Nome do profile base
        **kwargs: Overrides de configuração
    
    Returns:
        CrawlConfig configurado
    
    Example:
        >>> from seofrog import create_config
        >>> config = create_config('deep', max_urls=50000, delay=0.1)
    """
    
    from seofrog.core.config import create_config_from_profile, create_auto_config
    
    if profile:
        return create_config_from_profile(profile, **kwargs)
    else:
        return create_auto_config(**kwargs)

# === CLI INTEGRATION ===

def run_cli():
    """Entry point para CLI - usado em console_scripts"""
    from seofrog.main import main
    import sys
    sys.exit(main())

# === DEVELOPMENT HELPERS ===

def print_banner():
    """Print SEOFrog banner"""
    banner = f"""
🐸 =====================================================
   SEOFrog v{__version__} Enterprise 
   {__description__}
   {__url__}
🐸 =====================================================
"""
    print(banner)

def system_info():
    """Print informações do sistema"""
    info = get_version_info()
    print("🔍 INFORMAÇÕES DO SISTEMA:")
    print("=" * 40)
    for key, value in info.items():
        print(f"{key.replace('_', ' ').title()}: {value}")

# === MODULE DOCSTRING ===

__doc__ = f"""
SEOFrog v{__version__} Enterprise
{__description__}

Este é um clone profissional do Screaming Frog construído em Python,
otimizado para análise SEO enterprise com performance e escalabilidade.

Principais características:
- Crawling multi-threaded de alta performance
- Análise SEO completa (titles, meta tags, headers, links, images)
- Suporte a robots.txt e sitemaps.xml
- Sistema de configuração flexível com profiles
- Export para múltiplos formatos
- Logging enterprise com rotação
- Tratamento robusto de erros e retry inteligente

Uso básico:
    from seofrog import create_config, quick_crawl
    
    # Crawl rápido
    results = quick_crawl('https://example.com')
    
    # Configuração customizada
    config = create_config('deep', max_urls=100000, delay=0.1)

CLI Usage:
    seofrog https://example.com
    seofrog https://example.com --profile deep --max-urls 50000
    seofrog --analyze results.csv

Para mais informações, consulte a documentação em {__url__}
"""

if __name__ == "__main__":
    # Teste do package
    print_banner()
    system_info()
    print(f"\n📚 Package: {__name__}")
    print(f"📦 Version: {__version__}")
    print(f"📄 Exports: {len(__all__)} items")
    print(f"✅ Package loaded successfully!")