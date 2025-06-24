#!/usr/bin/env python3
"""
TESTE RÁPIDO: Verificação de Redirects Cafelor.com.br
Execute este script para confirmar o problema antes de aplicar as correções
"""

import requests
import urllib3
from urllib.parse import urljoin

# Suprime warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_redirect_quick(url):
    """Teste rápido de redirect"""
    try:
        response = requests.get(
            url, 
            allow_redirects=False, 
            timeout=5,
            verify=False,
            headers={'User-Agent': 'SEOFrog-Test/1.0'}
        )
        
        has_redirect = response.status_code in [301, 302, 303, 307, 308]
        location = response.headers.get('location', '') if has_redirect else ''
        final_url = urljoin(url, location) if location else url
        
        return {
            'url': url,
            'status': response.status_code,
            'redirect': has_redirect,
            'location': location,
            'final_url': final_url
        }
    except Exception as e:
        return {
            'url': url,
            'status': 0,
            'redirect': False,
            'error': str(e)
        }

def main():
    print("🔄 TESTE RÁPIDO DE REDIRECTS - CAFELOR.COM.BR")
    print("=" * 55)
    
    # URLs que o Screaming Frog detectou redirects
    test_urls = [
        "https://www.cafelor.com.br/Institucional/prazos-de-entrega-e-frete-gratis",
        "https://www.cafelor.com.br/compre-seu-cafe/capsulas/edicao-limitada", 
        "https://www.cafelor.com.br/compre-seu-cafe/d",
        "https://www.cafelor.com.br/lor-ferrari",
        "https://www.cafelor.com.br/compre-seu-cafe/capsulas/origens",
        "https://www.cafelor.com.br/reciclagem",
        "https://www.cafelor.com.br/compre-seu-cafe/soluvel/linha-regular",
        "https://www.cafelor.com.br/lor-kit-presenteavel-dia-dos-namorados-/p"
    ]
    
    redirects_found = 0
    total_tested = len(test_urls)
    
    print(f"🔍 Testando {total_tested} URLs que o Screaming Frog detectou redirects...\n")
    
    for i, url in enumerate(test_urls, 1):
        print(f"[{i}/{total_tested}] {url}")
        
        result = test_redirect_quick(url)
        
        if result.get('error'):
            print(f"   ❌ ERRO: {result['error']}")
        elif result['redirect']:
            redirects_found += 1
            print(f"   ✅ REDIRECT {result['status']}: {result['final_url']}")
        else:
            print(f"   ➖ SEM REDIRECT (Status: {result['status']})")
        
        print()
    
    # Resultado final
    print("📊 RESULTADO FINAL:")
    print(f"   URLs testadas: {total_tested}")
    print(f"   Redirects detectados: {redirects_found}")
    print(f"   Taxa de detecção: {(redirects_found/total_tested)*100:.1f}%")
    
    print("\n🎯 COMPARAÇÃO:")
    print(f"   Screaming Frog: ~50+ redirects detectados")
    print(f"   Teste rápido: {redirects_found} redirects detectados")
    
    if redirects_found >= 6:
        print("\n✅ DETECÇÃO BOA: O método básico está funcionando")
        print("💡 O problema pode estar na configuração do SEOFrog")
    elif redirects_found >= 3:
        print("\n⚠️  DETECÇÃO PARCIAL: Alguns redirects detectados")
        print("💡 Aplicar correções para melhorar cobertura")
    else:
        print("\n❌ DETECÇÃO RUIM: Poucos redirects detectados")
        print("💡 Urgente: aplicar todas as correções propostas")
    
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Aplicar correções no HTTPEngine")
    print("2. Adicionar RedirectDetector global") 
    print("3. Habilitar análise completa de redirects")
    print("4. Testar novamente com crawl completo")

if __name__ == "__main__":
    main()