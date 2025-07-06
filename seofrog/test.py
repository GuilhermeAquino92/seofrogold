#!/usr/bin/env python3
"""
Criação de Estrutura Completa SEOFrog
Cria todos os arquivos necessários para funcionamento
"""

import os
from pathlib import Path

def create_utils_init():
    """Cria __init__.py correto para seofrog.utils"""
    
    init_content = '''"""
seofrog.utils
Utilitários e helpers do SEOFrog v0.2 Enterprise
"""

# Imports principais
from .logger import get_logger, setup_logging

# URL Normalizer - import condicional para evitar erros
try:
    from .url_normalizer import URLNormalizer, normalize_url
    URL_NORMALIZER_AVAILABLE = True
except ImportError:
    URL_NORMALIZER_AVAILABLE = False
    
    # Fallback simples
    class URLNormalizer:
        def normalize(self, url):
            return url.lower().strip()
    
    def normalize_url(url):
        return url.lower().strip()

__all__ = [
    'get_logger',
    'setup_logging',
    'URLNormalizer', 
    'normalize_url',
    'URL_NORMALIZER_AVAILABLE'
]
'''
    
    utils_init_path = Path("seofrog/utils/__init__.py")
    utils_init_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(utils_init_path, 'w', encoding='utf-8') as f:
        f.write(init_content)
    
    print(f"✅ Criado: {utils_init_path}")

def create_basic_url_normalizer():
    """Cria url_normalizer.py básico se não existir"""
    
    url_normalizer_path = Path("seofrog/utils/url_normalizer.py")
    
    if url_normalizer_path.exists():
        print(f"✅ url_normalizer.py já existe ({url_normalizer_path.stat().st_size} bytes)")
        return
    
    basic_content = '''"""
seofrog/utils/url_normalizer.py
Normalizador básico de URLs para SEOFrog
"""

import re
from urllib.parse import urlparse, urlunparse, unquote
from typing import Optional

class URLNormalizer:
    """Normalizador básico de URLs"""
    
    def __init__(self):
        self.tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'gclid', 'fbclid', 'msclkid', 'twclid', '_ga', '_gl', 'ref'
        }
    
    def normalize(self, url: str) -> str:
        """
        Normaliza URL removendo parâmetros de tracking e padronizando formato
        
        Args:
            url: URL para normalizar
            
        Returns:
            URL normalizada
        """
        if not url or not isinstance(url, str):
            return ""
        
        try:
            # Limpa e decodifica URL
            url = unquote(url.strip())
            
            # Parse da URL
            parsed = urlparse(url.lower())
            
            # Normaliza componentes
            scheme = parsed.scheme or 'https'
            if scheme == 'http':
                scheme = 'https'  # Força HTTPS
            
            netloc = parsed.netloc
            
            # Normaliza path
            path = parsed.path or '/'
            path = re.sub(r'/+', '/', path)  # Remove duplas barras
            if path != '/' and path.endswith('/'):
                path = path[:-1]  # Remove trailing slash
            
            # Remove query parameters de tracking
            query = ""  # Por simplicidade, remove todos os params
            
            # Reconstrói URL
            normalized = urlunparse((scheme, netloc, path, "", query, ""))
            return normalized
            
        except Exception:
            return url  # Retorna original se der erro

def normalize_url(url: str) -> str:
    """Função de conveniência para normalizar URL"""
    normalizer = URLNormalizer()
    return normalizer.normalize(url)
'''
    
    with open(url_normalizer_path, 'w', encoding='utf-8') as f:
        f.write(basic_content)
    
    print(f"✅ Criado: {url_normalizer_path}")

def install_dependencies():
    """Instala dependências essenciais"""
    
    print("📦 INSTALANDO DEPENDÊNCIAS:")
    print("=" * 30)
    
    import subprocess
    import sys
    
    packages = [
        "beautifulsoup4",
        "lxml", 
        "requests",
        "pandas"
    ]
    
    for package in packages:
        try:
            print(f"📦 {package}...", end=" ")
            subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], check=True, capture_output=True)
            print("✅")
        except Exception:
            print("❌")

def test_structure():
    """Testa se estrutura está funcionando"""
    
    print("\n🧪 TESTANDO ESTRUTURA:")
    print("=" * 25)
    
    tests = [
        ("seofrog", "Módulo principal"),
        ("seofrog.utils", "Utils package"),
        ("seofrog.utils.url_normalizer", "URL Normalizer"),
    ]
    
    import sys
    current_dir = str(Path.cwd())
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    success_count = 0
    
    for module, description in tests:
        try:
            __import__(module)
            print(f"✅ {module} - {description}")
            success_count += 1
        except Exception as e:
            print(f"❌ {module} - {e}")
    
    # Teste específico URLNormalizer
    try:
        from seofrog.utils.url_normalizer import URLNormalizer, normalize_url
        normalizer = URLNormalizer()
        result = normalizer.normalize("HTTP://EXAMPLE.COM/page/")
        print(f"✅ URLNormalizer test: {result}")
        success_count += 1
    except Exception as e:
        print(f"❌ URLNormalizer test: {e}")
    
    print(f"\n📊 {success_count} testes passaram")
    return success_count >= 3

def create_quick_test_script():
    """Cria script de teste rápido"""
    
    test_content = '''#!/usr/bin/env python3
"""
Teste Rápido SEOFrog - Verificação de Funcionamento
"""

def test_seofrog():
    """Testa componentes básicos do SEOFrog"""
    
    print("🧪 Teste Rápido SEOFrog")
    print("=" * 25)
    
    try:
        # 1. Teste URLNormalizer
        from seofrog.utils.url_normalizer import URLNormalizer, normalize_url
        
        normalizer = URLNormalizer()
        test_url = "HTTP://EXAMPLE.COM/Page/?utm_source=test"
        result = normalizer.normalize(test_url)
        
        print(f"✅ URLNormalizer:")
        print(f"   Input:  {test_url}")
        print(f"   Output: {result}")
        
        # 2. Teste função de conveniência
        result2 = normalize_url("HTTPS://SITE.COM/page/")
        print(f"✅ normalize_url: {result2}")
        
        # 3. Teste logger
        from seofrog.utils.logger import get_logger
        logger = get_logger("Test")
        print("✅ Logger funcionando")
        
        print("\\n🎉 Todos os componentes básicos funcionando!")
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_seofrog()
'''
    
    with open("test_seofrog_quick.py", 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    print("✅ Criado: test_seofrog_quick.py")

def main():
    """Executa criação completa da estrutura"""
    
    print("🐸 SEOFrog - Criação de Estrutura Completa")
    print("=" * 50)
    
    # 1. Instala dependências
    install_dependencies()
    
    # 2. Cria estrutura de arquivos
    print("\n📁 CRIANDO ESTRUTURA:")
    print("=" * 25)
    
    create_utils_init()
    create_basic_url_normalizer()
    
    # 3. Testa estrutura
    if test_structure():
        print("\n🎉 SUCESSO! Estrutura criada e funcionando")
        
        # 4. Cria teste rápido
        create_quick_test_script()
        
        print("\n💡 PRÓXIMOS PASSOS:")
        print("   1. python test_seofrog_quick.py")
        print("   2. python -m seofrog https://www.cafelor.com.br --profile deep")
    else:
        print("\n⚠️ Ainda há problemas. Verifique os erros acima.")

if __name__ == "__main__":
    main()