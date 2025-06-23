"""
seofrog/core/config.py
Configurações enterprise do SEOFrog
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import os
from pathlib import Path

@dataclass
class CrawlConfig:
    """Configuração enterprise do crawler"""
    
    # === LIMITS ===
    max_urls: int = 500000
    max_depth: int = 50
    delay: float = 0.25
    timeout: int = 30
    max_workers: int = field(default_factory=lambda: os.cpu_count() or 4)
    
    # === BEHAVIOR ===
    respect_robots: bool = True
    follow_redirects: bool = True
    max_redirects: int = 10
    
    # === CONTENT TYPES ===
    crawl_images: bool = False
    crawl_css: bool = False
    crawl_js: bool = False
    crawl_pdf: bool = False
    
    # === NETWORK ===
    user_agent: str = "SEOFrog/0.2 (+https://seofrog.com/bot)"
    retry_attempts: int = 3
    retry_backoff: float = 2.0
    connection_pool_size: int = 100
    
    # === OUTPUT ===
    output_dir: str = "seofrog_output"
    log_level: str = "INFO"
    export_format: str = "xlsx"
    
    # === PERFORMANCE ===
    memory_limit_mb: int = 2048
    enable_compression: bool = True
    chunk_size: int = 8192
    
    # === ADVANCED ===
    custom_headers: Dict[str, str] = field(default_factory=dict)
    ignore_extensions: List[str] = field(default_factory=lambda: [
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
        '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.pdf', '.zip'
    ])
    
    def __post_init__(self):
        """Validação automática após inicialização"""
        self.validate()
        self._setup_output_dir()
    
    def validate(self) -> None:
        """Valida configuração enterprise"""
        if self.max_urls <= 0:
            raise ValueError("max_urls deve ser > 0")
            
        if self.max_workers <= 0 or self.max_workers > 100:
            raise ValueError("max_workers deve estar entre 1-100")
            
        if self.delay < 0:
            raise ValueError("delay não pode ser negativo")
            
        if self.timeout <= 0:
            raise ValueError("timeout deve ser > 0")
            
        if self.max_depth <= 0:
            raise ValueError("max_depth deve ser > 0")
            
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts não pode ser negativo")
            
        if self.memory_limit_mb <= 0:
            raise ValueError("memory_limit_mb deve ser > 0")
    
    def _setup_output_dir(self) -> None:
        """Cria diretório de output se não existir"""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte config para dict"""
        return {
            'max_urls': self.max_urls,
            'max_depth': self.max_depth,
            'delay': self.delay,
            'timeout': self.timeout,
            'max_workers': self.max_workers,
            'respect_robots': self.respect_robots,
            'follow_redirects': self.follow_redirects,
            'crawl_images': self.crawl_images,
            'crawl_css': self.crawl_css,
            'crawl_js': self.crawl_js,
            'user_agent': self.user_agent,
            'output_dir': self.output_dir,
            'log_level': self.log_level
        }

@dataclass 
class ProfileConfig:
    """Profile de configuração pré-definido"""
    name: str
    description: str
    config: CrawlConfig
    
    @classmethod
    def get_profiles(cls) -> Dict[str, 'ProfileConfig']:
        """Retorna profiles enterprise pré-definidos"""
        return {
            'quick': cls(
                name='quick',
                description='Teste rápido - 100 URLs, profundidade 3',
                config=CrawlConfig(
                    max_urls=100,
                    max_depth=3,
                    delay=0.1,
                    timeout=15,
                    max_workers=4
                )
            ),
            
            'standard': cls(
                name='standard', 
                description='Crawl padrão - 10k URLs, profundidade 10',
                config=CrawlConfig(
                    max_urls=10000,
                    max_depth=10,
                    delay=0.25,
                    timeout=30,
                    max_workers=os.cpu_count() or 8
                )
            ),
            
            'deep': cls(
                name='deep',
                description='Crawl profundo - 500k URLs, profundidade 50',
                config=CrawlConfig(
                    max_urls=500000,
                    max_depth=50,
                    delay=0.25,
                    timeout=30,
                    max_workers=os.cpu_count() or 8
                )
            ),
            
            'safe': cls(
                name='safe',
                description='Modo polite - delay alto, respeitoso',
                config=CrawlConfig(
                    max_urls=5000,
                    max_depth=8,
                    delay=1.0,
                    timeout=45,
                    max_workers=4,
                    retry_attempts=5
                )
            ),
            
            'aggressive': cls(
                name='aggressive',
                description='Modo agressivo - alta velocidade',
                config=CrawlConfig(
                    max_urls=100000,
                    max_depth=20,
                    delay=0.1,
                    timeout=20,
                    max_workers=(os.cpu_count() or 8) * 2,
                    retry_attempts=2
                )
            )
        }
    
    @classmethod
    def get_profile(cls, name: str) -> Optional['ProfileConfig']:
        """Retorna profile específico"""
        profiles = cls.get_profiles()
        return profiles.get(name.lower())
    
    @classmethod
    def list_profiles(cls) -> List[str]:
        """Lista nomes de todos os profiles"""
        return list(cls.get_profiles().keys())

# === FACTORY FUNCTIONS ===

def create_config_from_profile(profile_name: str, **overrides) -> CrawlConfig:
    """Cria config a partir de profile com overrides"""
    profile = ProfileConfig.get_profile(profile_name)
    if not profile:
        raise ValueError(f"Profile '{profile_name}' não encontrado")
    
    # Aplica overrides
    config_dict = profile.config.to_dict()
    config_dict.update(overrides)
    
    return CrawlConfig(**config_dict)

def create_auto_config(**overrides) -> CrawlConfig:
    """Cria config com auto-detection e overrides"""
    auto_workers = os.cpu_count() or 4
    
    base_config = {
        'max_workers': auto_workers,
        'memory_limit_mb': min(2048, (os.cpu_count() or 4) * 256)  # 256MB por core
    }
    
    base_config.update(overrides)
    return CrawlConfig(**base_config)

# === CONSTANTS ===

DEFAULT_USER_AGENTS = [
    "SEOFrog/0.2 (+https://seofrog.com/bot)",
    "Mozilla/5.0 (compatible; SEOFrog/0.2; +https://seofrog.com/bot)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 SEOFrog/0.2"
]

CRAWL_PRESETS = {
    'ecommerce': {
        'crawl_images': True,
        'max_depth': 15,
        'delay': 0.5
    },
    'blog': {
        'max_depth': 20,
        'delay': 0.2
    },
    'corporate': {
        'max_depth': 8,
        'delay': 0.3,
        'respect_robots': True
    }
}