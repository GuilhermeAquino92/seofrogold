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
            print(f"   ✅ {result['status']} → {result['final_url']}")
            redirects_found += 1
        else:
            print(f"   ⚪ {result['status']} (sem redirect)")
        
        print()
    
    print("=" * 55)
    print(f"📊 RESULTADO: {redirects_found}/{total_tested} redirects encontrados")
    
    if redirects_found > 0:
        print("✅ Redirects existem! O problema está no SEOFrog.")
    else:
        print("❌ Nenhum redirect encontrado. URLs podem ter mudado.")
    
    print("\n🔧 PRÓXIMOS PASSOS:")
    if redirects_found > 0:
        print("1. O HTTPEngine está detectando redirects mas perdendo os dados")
        print("2. Precisa corrigir o pipeline de dados no crawler")
        print("3. Garantir que redirect_chain chegue no CSV final")
    else:
        print("1. Verificar se URLs ainda redirecionam")
        print("2. Testar com outras URLs conhecidas")
        print("3. Revisar configuração do crawler")

if __name__ == "__main__":
    main()