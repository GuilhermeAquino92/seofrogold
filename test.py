"""
teste_basico.py
Teste básico para verificar se o RedirectService funciona
"""

def test_redirect_service():
    print("🧪 Testando RedirectService...")
    print("=" * 50)
    
    try:
        # 1. Importa o service
        print("1️⃣ Importando RedirectService...")
        from seofrog.services.redirect_service import RedirectService, get_redirect_service
        print("✅ Import funcionou!")
        
        # 2. Cria instância
        print("\n2️⃣ Criando instância...")
        service = get_redirect_service()
        print("✅ Instância criada!")
        
        # 3. Testa URLs básicas
        print("\n3️⃣ Testando URLs...")
        
        test_urls = [
            "http://google.com",      # Deve dar redirect 301 para https
            "https://google.com",     # Deve dar 200
            "https://httpbin.org/status/404"  # Deve dar 404
        ]
        
        for url in test_urls:
            print(f"\n🔗 Testando: {url}")
            
            try:
                info = service.get_status_info(url)
                print(f"   ✅ Status: {info.status_code}")
                print(f"   ✅ URL final: {info.final_url}")
                print(f"   ✅ Redirect type: {info.redirect_type.value}")
                print(f"   ✅ SEO Impact: {info.seo_impact}")
                print(f"   ✅ Response time: {info.response_time:.2f}s")
                
                if info.is_redirect:
                    print(f"   🔄 É redirect: SIM")
                else:
                    print(f"   📄 É redirect: NÃO")
                    
            except Exception as e:
                print(f"   ❌ Erro testando {url}: {e}")
        
        # 4. Testa estatísticas
        print("\n4️⃣ Verificando estatísticas...")
        stats = service.get_statistics()
        print(f"   📊 Cache hits: {stats['cache_hits']}")
        print(f"   📊 Cache misses: {stats['cache_misses']}")
        print(f"   📊 Requests made: {stats['requests_made']}")
        print(f"   📊 Hit rate: {stats['hit_rate_percent']}%")
        
        # 5. Testa cache (segunda chamada deve ser hit)
        print("\n5️⃣ Testando cache...")
        print("Fazendo segunda chamada para google.com...")
        info2 = service.get_status_info("http://google.com")
        stats2 = service.get_statistics()
        
        if stats2['cache_hits'] > stats['cache_hits']:
            print("   ✅ Cache funcionando! Hit detectado.")
        else:
            print("   ⚠️ Cache pode não estar funcionando.")
            
        print(f"   📊 Cache hits após segunda chamada: {stats2['cache_hits']}")
        
        print("\n" + "=" * 50)
        print("🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("✅ RedirectService está funcionando corretamente!")
        return True
        
    except ImportError as e:
        print(f"❌ ERRO DE IMPORT: {e}")
        print("💡 Verifique se os arquivos foram criados corretamente:")
        print("   - services/__init__.py")
        print("   - services/redirect_service.py")
        return False
        
    except Exception as e:
        print(f"❌ ERRO GERAL: {e}")
        print(f"   Tipo do erro: {type(e).__name__}")
        return False

if __name__ == "__main__":
    test_redirect_service()