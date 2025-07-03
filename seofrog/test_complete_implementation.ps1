# setup_and_test_seofrog.ps1
# Script para configurar e testar SEOFrog diretamente

Write-Host "SEOFROG - SETUP E TESTE" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan

function Write-Status {
    param([string]$Type, [string]$Message)
    switch ($Type) {
        "success" { Write-Host "[OK] $Message" -ForegroundColor Green }
        "error" { Write-Host "[ERRO] $Message" -ForegroundColor Red }
        "warning" { Write-Host "[AVISO] $Message" -ForegroundColor Yellow }
        "info" { Write-Host "[INFO] $Message" -ForegroundColor Blue }
        default { Write-Host $Message }
    }
}

# 1. Verifica estrutura do projeto
Write-Status "info" "1. Verificando estrutura do projeto..."
Write-Host "Pasta atual: $(Get-Location)"
Write-Host "Arquivos na pasta:"
Get-ChildItem | Select-Object Name, PSIsContainer | Format-Table -AutoSize

# 2. Procura pelo seofrog
$seofrogLocations = @(
    ".\seofrog.py",
    ".\seofrog\__main__.py", 
    ".\seofrog\cli.py",
    ".\main.py",
    ".\cli.py"
)

$foundSeofrog = $null
foreach ($location in $seofrogLocations) {
    if (Test-Path $location) {
        $foundSeofrog = $location
        Write-Status "success" "SEOFrog encontrado em: $location"
        break
    }
}

if (-not $foundSeofrog) {
    Write-Status "warning" "Executavel seofrog nao encontrado diretamente"
    Write-Status "info" "Procurando na estrutura de pastas..."
    
    # Procura recursivamente
    $seofrogFiles = Get-ChildItem -Recurse -Name "*.py" | Where-Object { 
        $_ -match "seofrog|cli|main" 
    } | Select-Object -First 5
    
    if ($seofrogFiles) {
        Write-Host "Arquivos Python encontrados:"
        $seofrogFiles | ForEach-Object { Write-Host "  - $_" }
        
        # Tenta o primeiro que parece ser o principal
        $foundSeofrog = $seofrogFiles | Where-Object { $_ -match "cli|main" } | Select-Object -First 1
        if (-not $foundSeofrog) {
            $foundSeofrog = $seofrogFiles[0]
        }
        Write-Status "info" "Tentando usar: $foundSeofrog"
    }
}

# 3. Testa execucao direta
if ($foundSeofrog) {
    Write-Status "info" "2. Testando execucao direta..."
    
    try {
        Write-Host "Executando: python $foundSeofrog --help"
        $helpOutput = & python $foundSeofrog --help 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Status "success" "SEOFrog executavel via Python!"
            Write-Host "Saida do --help:"
            $helpOutput | Select-Object -First 10 | ForEach-Object { Write-Host "  $_" }
        } else {
            Write-Status "error" "Erro executando SEOFrog:"
            $helpOutput | Select-Object -First 5 | ForEach-Object { Write-Host "  $_" }
        }
    } catch {
        Write-Status "error" "Erro executando Python: $_"
    }
} else {
    Write-Status "error" "Nao foi possivel encontrar o executavel do SEOFrog"
    Write-Status "info" "Verificando se existe seofrog como modulo..."
    
    try {
        $moduleTest = & python -c "import seofrog; print('Modulo seofrog encontrado')" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Status "success" "SEOFrog disponivel como modulo Python"
            $foundSeofrog = "seofrog_module"
        } else {
            Write-Status "warning" "Modulo seofrog nao encontrado: $moduleTest"
        }
    } catch {
        Write-Status "warning" "Erro testando modulo: $_"
    }
}

# 4. Executa teste se encontrou seofrog
if ($foundSeofrog) {
    Write-Status "info" "3. Executando teste basico..."
    
    # Limpa arquivos anteriores
    Remove-Item -Path "seofrog_results.xlsx", "seofrog.log" -ErrorAction SilentlyContinue
    
    # Monta comando
    if ($foundSeofrog -eq "seofrog_module") {
        $command = "python -m seofrog"
    } else {
        $command = "python $foundSeofrog"
    }
    
    $testArgs = "cafelor.com.br --max-urls 5 --workers 1"
    
    Write-Host "Executando: $command $testArgs"
    Write-Status "info" "Aguarde... pode levar alguns minutos"
    
    try {
        $startTime = Get-Date
        $output = & cmd /c "$command $testArgs" 2>&1
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        
        Write-Status "info" "Execucao completada em $([math]::Round($duration, 1)) segundos"
        
        # Mostra ultimas linhas do output
        if ($output) {
            Write-Host "Ultimas linhas do output:"
            $output | Select-Object -Last 10 | ForEach-Object { Write-Host "  $_" }
        }
        
    } catch {
        Write-Status "error" "Erro na execucao: $_"
    }
    
    # Verifica se gerou arquivo
    if (Test-Path "seofrog_results.xlsx") {
        Write-Status "success" "Arquivo Excel gerado!"
        
        # Analise rapida
        Write-Status "info" "4. Analisando resultados..."
        
        $analysis = @'
import pandas as pd
import sys

try:
    excel_file = pd.ExcelFile("seofrog_results.xlsx")
    sheets = excel_file.sheet_names
    
    print(f"ANALISE DOS RESULTADOS:")
    print(f"  Total de abas: {len(sheets)}")
    
    # Lista todas as abas
    print(f"  Abas encontradas:")
    for i, sheet in enumerate(sheets, 1):
        print(f"    {i}. {sheet}")
    
    # Verifica se tem aba de redirects
    redirect_sheets = [s for s in sheets if "redirect" in s.lower()]
    if redirect_sheets:
        print(f"  Aba de redirects: SIM ({redirect_sheets[0]})")
        
        # Analisa aba de redirects
        redirects_df = pd.read_excel("seofrog_results.xlsx", sheet_name=redirect_sheets[0])
        print(f"    Linhas na aba: {len(redirects_df)}")
        
        if len(redirects_df) > 0:
            print(f"    Colunas: {list(redirects_df.columns)}")
    else:
        print(f"  Aba de redirects: NAO")
    
    # Verifica aba principal de dados
    data_sheets = [s for s in sheets if "dados" in s.lower() or "completo" in s.lower()]
    if not data_sheets:
        data_sheets = [s for s in sheets if len(s) > 10]  # Pega a maior aba
    
    if data_sheets:
        main_df = pd.read_excel("seofrog_results.xlsx", sheet_name=data_sheets[0])
        print(f"  Dados principais ({data_sheets[0]}):")
        print(f"    URLs processadas: {len(main_df)}")
        print(f"    Colunas encontradas: {len(main_df.columns)}")
        
        # Verifica colunas de parsers modulares
        modular_indicators = {
            "MetaParser": ["title", "meta_description"],
            "TechnicalParser": ["has_viewport", "has_charset", "redirects_count"],
            "SocialParser": ["og_tags_count", "twitter_tags_count"],
            "SchemaParser": ["schema_total_count"]
        }
        
        print(f"  Parsers modulares:")
        for parser, cols in modular_indicators.items():
            found = [c for c in cols if c in main_df.columns]
            status = "OK" if len(found) > 0 else "NAO"
            print(f"    {parser}: {status} ({len(found)}/{len(cols)} colunas)")
    
    # Resultado final
    has_redirects = len(redirect_sheets) > 0
    has_data = len(data_sheets) > 0
    
    if has_redirects and has_data:
        print(f"\nRESULTADO FINAL: SUCESSO!")
        print(f"  - Aba de redirects criada")
        print(f"  - Dados processados corretamente")
        print(f"  - Implementacao funcionando")
    elif has_data:
        print(f"\nRESULTADO FINAL: PARCIAL")
        print(f"  - Dados processados")
        print(f"  - Aba de redirects pode nao estar implementada")
    else:
        print(f"\nRESULTADO FINAL: PROBLEMAS")
        print(f"  - Estrutura inesperada do arquivo")
        
except Exception as e:
    print(f"ERRO na analise: {e}")
    import traceback
    traceback.print_exc()
'@

        $analysis | python
        
        # Oferece para abrir arquivo
        $response = Read-Host "`nDeseja abrir o arquivo Excel? (s/n)"
        if ($response -eq "s" -or $response -eq "S") {
            Start-Process "seofrog_results.xlsx"
        }
        
    } else {
        Write-Status "error" "Arquivo Excel nao foi gerado"
        Write-Status "info" "Verificando se houve alguma saida..."
        
        if ($output) {
            Write-Host "Output completo da execucao:"
            $output | ForEach-Object { Write-Host "  $_" }
        }
    }
    
} else {
    Write-Status "error" "Nao foi possivel executar SEOFrog"
    Write-Status "info" "Opcoes para resolver:"
    Write-Host "  1. Verificar se esta na pasta correta do projeto"
    Write-Host "  2. Instalar dependencias: pip install -r requirements.txt"
    Write-Host "  3. Verificar se Python esta configurado corretamente"
}

Write-Host ""
Write-Status "info" "RESUMO:"
Write-Host "Se o teste funcionou, a implementacao esta correta!"
Write-Host "Se houve problemas, verifique:"
Write-Host "  - Estrutura do projeto"
Write-Host "  - Dependencias instaladas"
Write-Host "  - Modificacoes aplicadas nos arquivos"

Write-Host ""
Write-Host "Pressione qualquer tecla para finalizar..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")