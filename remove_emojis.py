"""Script para remover emojis dos arquivos Python"""

import re
from pathlib import Path

def remove_emojis_from_file(file_path):
    """Remove emojis de um arquivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Mapeamento de emojis para texto
        emoji_replacements = {
            '🐸': '',
            '🚀': '',
            '📋': '',
            '🤖': '',
            '💡': '',
            '⚠️': 'WARNING:',
            '✅': 'OK:',
            '❌': 'ERROR:',
            '📊': '',
            '🔧': '',
            '🕷️': '',
            '🌐': '',
            '📁': '',
            '🎯': '',
            '⏱️': '',
            '📈': '',
            '🏁': '',
            '🛡️': '',
            '🔄': '',
            '💾': '',
            '🎉': '',
            '⏹️': '',
            '▶️': '',
            '⏸️': '',
            '🔓': '',
            '🔒': '',
            '📝': '',
            '🎨': '',
            '🔍': '',
            '⚡': '',
            '🌟': '',
            '🎪': '',
            '🎭': '',
            '🎬': '',
            '🎵': '',
            '🎶': '',
            '🎼': ''
        }
        
        # Remove emojis conhecidos
        for emoji, replacement in emoji_replacements.items():
            content = content.replace(emoji, replacement)
        
        # Remove caracteres Unicode de emoji (U+1F000 to U+1F9FF)
        content = re.sub(r'[\U0001F000-\U0001F9FF]', '', content)
        
        # Remove outros símbolos Unicode comuns
        content = re.sub(r'[\u2600-\u26FF\u2700-\u27BF]', '', content)
        
        # Limpa espaços extras
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r' +', ' ', content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Processado: {file_path}")
        return True
        
    except Exception as e:
        print(f"Erro processando {file_path}: {e}")
        return False

def main():
    """Remove emojis de arquivos específicos"""
    files_to_clean = [
        'seofrog/cli.py',
        'seofrog/main.py',
        'seofrog/utils/validators.py',
        'seofrog/utils/banner.py'
    ]
    
    for file_path in files_to_clean:
        full_path = Path(file_path)
        if full_path.exists():
            remove_emojis_from_file(full_path)
        else:
            print(f"Arquivo não encontrado: {file_path}")

if __name__ == "__main__":
    main()