#!/usr/bin/env python3
"""
Correção Rápida Linha 195
"""

import os
import shutil

def fix_crawler():
    """Aplica correções no crawler.py"""
    
    crawler_path = "core/crawler.py"
    
    # Backup
    backup_path = crawler_path + ".backup"
    shutil.copy2(crawler_path, backup_path)
    print(f"📁 Backup: {backup_path}")
    
    # Lê arquivo
    with open(crawler_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove caracteres problemáticos
    import re
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
    
    # Salva versão limpa
    with open(crawler_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)
    
    print("✅ Arquivo limpo!")
    
    # Teste final
    try:
        import ast
        ast.parse(cleaned)
        print("✅ Sintaxe corrigida!")
        return True
    except SyntaxError as e:
        print(f"❌ Ainda há erro: {e}")
        return False

if __name__ == "__main__":
    fix_crawler()
