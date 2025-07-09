#!/usr/bin/env python3
"""
Script para aplicar automaticamente o patch was_hit() no RedirectCache
Execute: python auto_patch_was_hit.py
"""

import re
from pathlib import Path

def apply_was_hit_patch():
    """
    Aplica automaticamente as modificações necessárias para implementar was_hit()
    """
    
    cache_file = Path('seofrog/utils/redirect_cache.py')
    
    if not cache_file.exists():
        print(f"❌ Arquivo não encontrado: {cache_file}")
        print("Execute este script no diretório raiz do projeto SEOFrog")
        return False
    
    print(f"🔧 Aplicando patch was_hit() em {cache_file}")
    
    # Backup do arquivo original
    backup_file = cache_file.with_suffix('.py.backup')
    if not backup_file.exists():
        cache_file.rename(backup_file)
        print(f"📦 Backup criado: {backup_file}")
    else:
        print(f"📦 Backup já existe: {backup_file}")
    
    # Lê arquivo original
    with open(backup_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("🔧 Aplicando modificações...")
    
    # MODIFICAÇÃO 1: Adicionar self._last_was_hit = False no __init__
    pattern1 = r"(self\._errors = 0\s*\n\s*)(self\.logger = get_logger\('RedirectCache'\))"
    replacement1 = r"\1\n        # ✅ was_hit() implementation\n        self._last_was_hit = False\n        \n        \2"
    content = re.sub(pattern1, replacement1, content)
    
    # MODIFICAÇÃO 2: Adicionar self._last_was_hit = True no cache hit
    pattern2 = r"(if cached_result:\s*\n\s*self\._hits \+= 1\s*\n)"
    replacement2 = r"\1            self._last_was_hit = True  # ✅ Cache hit\n"
    content = re.sub(pattern2, replacement2, content)
    
    # MODIFICAÇÃO 3: Adicionar self._last_was_hit = False no cache miss
    pattern3 = r"(self\._misses \+= 1\s*\n)"
    replacement3 = r"\1        self._last_was_hit = False  # ✅ Cache miss\n"
    content = re.sub(pattern3, replacement3, content)
    
    # MODIFICAÇÃO 4: Adicionar método was_hit() antes de get_stats
    pattern4 = r"(\s*)(def get_stats\(self\) -> Dict\[str, Any\]:)"
    was_hit_method = '''
    def was_hit(self) -> bool:
        """
        Retorna se a última chamada get_or_fetch() foi cache hit
        
        Returns:
            bool: True se último request foi cache hit, False se cache miss
        """
        return self._last_was_hit

    '''
    replacement4 = f"{was_hit_method}\\1\\2"
    content = re.sub(pattern4, replacement4, content)
    
    # MODIFICAÇÃO 5: Adicionar last_was_hit no get_stats return
    pattern5 = r"('cache_file': str\(self\.cache_path\))"
    replacement5 = r"\1,\n                'last_was_hit': self._last_was_hit"
    content = re.sub(pattern5, replacement5, content)
    
    # MODIFICAÇÃO 6: Adicionar reset no clear_cache
    pattern6 = r"(self\._errors = 0\s*\n)(\s*self\.logger\.info)"
    replacement6 = r"\1                self._last_was_hit = False\n\n\2"
    content = re.sub(pattern6, replacement6, content)
    
    # Escreve arquivo modificado
    with open(cache_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Patch aplicado com sucesso!")
    return True

def test_was_hit_implementation():
    """
    Testa se a implementação was_hit() funciona corretamente
    """
    try:
        import sys
        sys.path.insert(0, '.')
        
        from seofrog.utils.redirect_cache import RedirectCache
        
        print("\n🧪 Testando implementação was_hit()...")
        
        # Verifica se método existe
        cache = RedirectCache()
        if not hasattr(cache, 'was_hit'):
            print("❌ Método was_hit() não foi implementado corretamente")
            return False
        
        print("✅ Método was_hit() encontrado")
        
        # Teste funcional básico
        print("🔬 Testando funcionalidade...")
        
        # Primeira chamada = cache miss
        url1, status1 = cache.get_or_fetch("https://httpbin.org/status/200")
        hit1 = cache.was_hit()
        print(f"   1ª chamada: was_hit = {hit1} (esperado: False)")
        
        # Segunda chamada = cache hit
        url2, status2 = cache.get_or_fetch("https://httpbin.org/status/200")
        hit2 = cache.was_hit()
        print(f"   2ª chamada: was_hit = {hit2} (esperado: True)")
        
        # Terceira chamada nova URL = cache miss
        url3, status3 = cache.get_or_fetch("https://httpbin.org/status/404")
        hit3 = cache.was_hit()
        print(f"   3ª chamada: was_hit = {hit3} (esperado: False)")
        
        # Validação
        if not hit1 and hit2 and not hit3:
            print("🎯 ✅ was_hit() funcionando PERFEITAMENTE!")
            
            # Testa estatísticas
            stats = cache.get_stats()
            if 'last_was_hit' in stats:
                print(f"📊 Estatísticas: last_was_hit = {stats['last_was_hit']}")
                print("✅ Integração completa funcionando!")
                return True
            else:
                print("⚠️ was_hit() funciona mas estatísticas não foram atualizadas")
                return False
        else:
            print("❌ was_hit() implementado mas com comportamento inesperado")
            return False
            
    except ImportError as e:
        print(f"❌ Erro importando RedirectCache: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro testando was_hit(): {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Auto-Patch: Implementação was_hit() no RedirectCache")
    print("=" * 60)
    
    # Aplica patch
    if apply_was_hit_patch():
        print("\n🧪 Testando implementação...")
        
        # Testa implementação
        if test_was_hit_implementation():
            print("\n🎉 SUCESSO COMPLETO!")
            print("✅ was_hit() implementado e funcionando")
            print("✅ Erro AttributeError deve ter desaparecido")
            print("✅ RedirectCache otimizado para performance")
            
            print("\n🚀 Próximos passos:")
            print("1. Execute: seofrog https://seusite.com --timeout 15 --max-urls 20")
            print("2. Verifique se erro 'was_hit' sumiu dos logs")
            print("3. Procure por logs '✅ TYPO REDIRECT detectado'")
            print("4. Confirme se aba 'Internal' foi criada")
            
            return 0
        else:
            print("\n❌ Patch aplicado mas teste falhou")
            print("Verifique se há erros de sintaxe no arquivo")
            return 1
    else:
        print("\n❌ Falha aplicando patch")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())