"""
seofrog/parsers/headings_parser.py
Parser modular para análise completa de headings H1-H6
Inclui detecção de headings vazias e escondidas por CSS
"""

from typing import Dict, Any, List
from bs4 import BeautifulSoup, Tag
from .base import ParserMixin, SEO_LIMITS, SeverityLevel

class HeadingsParser(ParserMixin):
    """
    Parser especializado para análise completa de headings
    Responsável por: H1-H6, detecção de vazias/escondidas, estrutura hierárquica
    """
    
    def __init__(self):
        super().__init__()
    
    def parse(self, soup: BeautifulSoup, word_count: int = None) -> Dict[str, Any]:
        """
        Parse completo de todas as headings com análise avançada
        
        Args:
            soup: BeautifulSoup object da página
            word_count: Word count real da página (do content_parser, opcional)
            
        Returns:
            Dict com dados completos de headings
        """
        data = {}
        
        try:
            # Parse básico de todas as headings H1-H6
            self._parse_basic_headings(soup, data)
            
            # Análise avançada de headings problemáticas
            self._analyze_empty_headings(soup, data)
            self._analyze_hidden_headings(soup, data)
            
            # Análise da estrutura hierárquica
            self._analyze_heading_structure(soup, data)
            
            # Métricas de qualidade (🆕 aceita word_count real)
            self._calculate_heading_metrics(data, word_count)
            
            # 🆕 SEVERITY SCORING
            self._calculate_severity_score(data)
            
            # Log estatísticas
            errors = 1 if any(key.endswith('_error') for key in data.keys()) else 0
            self.log_parsing_stats('HeadingsParser', len(data), errors)
            
        except Exception as e:
            self.logger.error(f"Erro no parse de headings: {e}")
            data['headings_parse_error'] = str(e)
            self.log_parsing_stats('HeadingsParser', len(data), 1)
        
        return data
    
    def _parse_basic_headings(self, soup: BeautifulSoup, data: Dict):
        """
        Parse básico de contagem e texto das headings H1-H6
        """
        # Contagem de cada nível de heading
        for level in range(1, 7):
            headings = self.safe_find_all(soup, f'h{level}')
            data[f'h{level}_count'] = len(headings)
            
            # Para H1, extrai também o texto da primeira ocorrência
            if level == 1 and headings:
                h1_text = self.extract_text_safe(headings[0])
                data['h1_text'] = h1_text
                data['h1_length'] = len(h1_text)
                
                # Análise de qualidade do H1
                h1_analysis = self.analyze_text_length(
                    h1_text,
                    SEO_LIMITS.get('h1', {}).get('min', 10),
                    SEO_LIMITS.get('h1', {}).get('max', 70)
                )
                data['h1_is_empty'] = h1_analysis['is_empty']
                data['h1_too_short'] = h1_analysis['too_short']
                data['h1_too_long'] = h1_analysis['too_long']
                data['h1_optimal_length'] = h1_analysis['optimal']
                
            elif level == 1:
                # Sem H1
                data['h1_text'] = ''
                data['h1_length'] = 0
                data['h1_is_empty'] = True
                data['h1_too_short'] = False
                data['h1_too_long'] = False
                data['h1_optimal_length'] = False
        
        # Contagem total de headings
        data['total_headings_count'] = sum(data[f'h{i}_count'] for i in range(1, 7))
    
    def _analyze_empty_headings(self, soup: BeautifulSoup, data: Dict):
        """
        Detecta e analisa headings vazias
        """
        empty_headings = []
        
        for level in range(1, 7):
            headings = self.safe_find_all(soup, f'h{level}')
            
            for heading in headings:
                heading_text = self.extract_text_safe(heading)
                
                if self._is_empty_heading(heading_text):
                    empty_headings.append({
                        'level': f'H{level}',
                        'text': heading_text,
                        'html': str(heading)[:200],  # Primeiros 200 chars
                        'reason': self._get_empty_reason(heading_text, str(heading))
                    })
        
        # Adiciona aos dados
        data['empty_headings_count'] = len(empty_headings)
        data['empty_headings_details'] = empty_headings
        
        # Resumo textual para CSV/análise
        if empty_headings:
            summary_parts = []
            for h in empty_headings:
                summary_parts.append(f"{h['level']}: {h['reason']}")
            data['empty_headings_summary'] = '; '.join(summary_parts)
        else:
            data['empty_headings_summary'] = ''
    
    def _analyze_hidden_headings(self, soup: BeautifulSoup, data: Dict):
        """
        Detecta headings escondidas por CSS (técnica SEO suspeita)
        """
        hidden_headings = []
        
        for level in range(1, 7):
            headings = self.safe_find_all(soup, f'h{level}')
            
            for heading in headings:
                heading_text = self.extract_text_safe(heading)
                
                if self.is_hidden_by_css(heading):  # 🆕 Usa helper centralizado
                    hidden_headings.append({
                        'level': f'H{level}',
                        'text': heading_text,
                        'html': str(heading)[:200],
                        'css_issue': self.get_css_hiding_method(heading)  # 🆕 Usa helper centralizado
                    })
        
        # Adiciona aos dados
        data['hidden_headings_count'] = len(hidden_headings)
        data['hidden_headings_details'] = hidden_headings
        
        # Resumo textual para CSV/análise
        if hidden_headings:
            summary_parts = []
            for h in hidden_headings:
                summary_parts.append(f"{h['level']}: {h['css_issue']}")
            data['hidden_headings_summary'] = '; '.join(summary_parts)
        else:
            data['hidden_headings_summary'] = ''
    
    def _analyze_heading_structure(self, soup: BeautifulSoup, data: Dict):
        """
        Analisa a estrutura hierárquica das headings (boa prática SEO)
        """
        # Verifica se há pelo menos um H1
        data['has_h1'] = data.get('h1_count', 0) > 0
        
        # Verifica se há apenas um H1 (recomendado)
        data['single_h1'] = data.get('h1_count', 0) == 1
        
        # Verifica se há múltiplos H1 (problemático)
        data['multiple_h1'] = data.get('h1_count', 0) > 1
        
        # Verifica estrutura hierárquica básica (H1 → H2 → H3...)
        structure_issues = []
        
        # Se tem H1 mas não tem H2
        if data.get('h1_count', 0) > 0 and data.get('h2_count', 0) == 0:
            structure_issues.append('H1 sem H2 subsequente')
        
        # Se tem H3 mas não tem H2
        if data.get('h3_count', 0) > 0 and data.get('h2_count', 0) == 0:
            structure_issues.append('H3 sem H2 precedente')
        
        # Se tem H4 mas não tem H3
        if data.get('h4_count', 0) > 0 and data.get('h3_count', 0) == 0:
            structure_issues.append('H4 sem H3 precedente')
        
        data['heading_structure_issues'] = structure_issues
        data['heading_structure_valid'] = len(structure_issues) == 0
    
    def _calculate_heading_metrics(self, data: Dict, word_count: int = None):
        """
        Calcula métricas de qualidade das headings
        
        Args:
            data: Dados das headings
            word_count: Word count real da página (do content_parser, opcional)
        """
        # Score de estrutura (0-100)
        structure_score_items = [
            data.get('has_h1', False),                    # Tem H1
            data.get('single_h1', False),                 # H1 único
            data.get('h2_count', 0) > 0,                  # Tem H2
            data.get('heading_structure_valid', False),   # Estrutura hierárquica válida
            data.get('empty_headings_count', 0) == 0,     # Sem headings vazias
            data.get('hidden_headings_count', 0) == 0     # Sem headings escondidas
        ]
        
        data['heading_structure_score'] = int((sum(structure_score_items) / len(structure_score_items)) * 100)
        
        # Densidade de headings (headings por 100 palavras)
        total_headings = data.get('total_headings_count', 0)
        if total_headings > 0:
            if word_count:
                # 🆕 Word count real do content_parser
                data['heading_density_real'] = (total_headings / word_count) * 100
                data['heading_density_source'] = 'real'
            else:
                # Estimativa: página típica tem ~500 palavras
                estimated_words = 500
                data['heading_density_estimate'] = (total_headings / estimated_words) * 100
                data['heading_density_source'] = 'estimated'
        else:
            data['heading_density_real'] = 0
            data['heading_density_estimate'] = 0
            data['heading_density_source'] = 'none'
    
    def _calculate_severity_score(self, data: Dict):
        """
        🆕 Calcula score de severidade baseado nos problemas encontrados
        """
        problems_keys = []
        
        # Identifica problemas por prioridade
        if not data.get('has_h1'):
            problems_keys.append('sem_h1')
        elif data.get('multiple_h1'):
            problems_keys.append('multiplos_h1')
        
        if data.get('h1_is_empty'):
            problems_keys.append('h1_vazio')
        elif data.get('h1_too_short'):
            problems_keys.append('h1_muito_curto')
        elif data.get('h1_too_long'):
            problems_keys.append('h1_muito_longo')
        
        if data.get('empty_headings_count', 0) > 0:
            problems_keys.append('headings_vazias')
        
        if data.get('hidden_headings_count', 0) > 0:
            problems_keys.append('headings_escondidas')
        
        if not data.get('heading_structure_valid'):
            problems_keys.append('estrutura_hierarquica_invalida')
        
        if data.get('h2_count', 0) == 0 and data.get('h1_count', 0) > 0:
            problems_keys.append('sem_h2')
        
        # Calcula severidade geral usando helper do ParserMixin
        data['heading_severity_level'] = self.calculate_problem_severity(problems_keys)
        data['heading_problems_keys'] = problems_keys
        
        # Categoriza problemas por severidade
        data['heading_problems_by_severity'] = self.categorize_problems_by_severity(problems_keys)
    
    # ==========================================
    # MÉTODOS AUXILIARES PARA DETECÇÃO
    # ==========================================
    
    def _is_empty_heading(self, text: str) -> bool:
        """
        Verifica se heading está vazia (casos realmente vazios)
        
        Args:
            text: Texto da heading
            
        Returns:
            bool: True se heading vazia
        """
        if not text:
            return True
        
        # Remove espaços em branco
        clean_text = text.replace('\n', '').replace('\t', '').replace('\r', '').strip()
        
        # Verifica padrões de texto vazio
        empty_patterns = [
            '',        # Completamente vazio
            '&nbsp;',  # Non-breaking space HTML
            '\u00a0',  # Non-breaking space Unicode
        ]
        
        # Verifica se é só espaços em branco
        if len(clean_text) == 0:
            return True
            
        return clean_text in empty_patterns
    
    def _get_empty_reason(self, text: str, html: str) -> str:
        """
        Identifica o motivo da heading estar vazia
        
        Args:
            text: Texto da heading
            html: HTML da heading
            
        Returns:
            str: Motivo identificado
        """
        if not text:
            return "Completamente vazia"
        
        clean_text = text.strip()
        
        if '&nbsp;' in html:
            return "Contém &nbsp;"
        elif clean_text == '\u00a0':
            return "Non-breaking space"
        elif len(clean_text) == 0:
            return "Só espaços em branco"
        else:
            return "Vazia"
    
    # ==========================================
    # MÉTODOS DE ANÁLISE E RELATÓRIOS
    # ==========================================
    
    def get_heading_summary(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera resumo dos problemas de headings encontrados
        
        Args:
            parsed_data: Dados já parseados pelo método parse()
            
        Returns:
            Dict com resumo de problemas
        """
        problems = []
        critical_issues = []
        
        # Problemas estruturais críticos
        if not parsed_data.get('has_h1'):
            problems.append('Página sem H1')
            critical_issues.append('Sem H1')
        elif parsed_data.get('multiple_h1'):
            problems.append('Múltiplos H1 na página')
            critical_issues.append('Múltiplos H1')
        
        # Problemas de conteúdo
        if parsed_data.get('h1_is_empty'):
            problems.append('H1 vazio')
            critical_issues.append('H1 vazio')
        elif parsed_data.get('h1_too_short'):
            problems.append('H1 muito curto')
        elif parsed_data.get('h1_too_long'):
            problems.append('H1 muito longo')
        
        # Problemas técnicos
        empty_count = parsed_data.get('empty_headings_count', 0)
        if empty_count > 0:
            problems.append(f'{empty_count} headings vazias')
        
        hidden_count = parsed_data.get('hidden_headings_count', 0)
        if hidden_count > 0:
            problems.append(f'{hidden_count} headings escondidas (suspeito)')
            critical_issues.append('Headings escondidas')
        
        # Problemas de estrutura
        structure_issues = parsed_data.get('heading_structure_issues', [])
        if structure_issues:
            problems.extend(structure_issues)
        
        return {
            'heading_problems_count': len(problems),
            'heading_problems_list': problems,
            'heading_critical_issues': critical_issues,
            'heading_has_critical_issues': len(critical_issues) > 0,
            'heading_structure_score': parsed_data.get('heading_structure_score', 0),
            # 🆕 Severity information
            'heading_severity_level': parsed_data.get('heading_severity_level', SeverityLevel.BAIXA),
            'heading_problems_by_severity': parsed_data.get('heading_problems_by_severity', {})
        }
    
    def validate_heading_best_practices(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida boas práticas de headings
        
        Args:
            parsed_data: Dados já parseados
            
        Returns:
            Dict com validações de boas práticas
        """
        validations = {}
        
        # Estrutura básica
        validations['has_single_h1'] = parsed_data.get('single_h1', False)
        validations['h1_not_empty'] = not parsed_data.get('h1_is_empty', True)
        validations['h1_optimal_length'] = parsed_data.get('h1_optimal_length', False)
        validations['has_h2_structure'] = parsed_data.get('h2_count', 0) > 0
        
        # Qualidade técnica
        validations['no_empty_headings'] = parsed_data.get('empty_headings_count', 0) == 0
        validations['no_hidden_headings'] = parsed_data.get('hidden_headings_count', 0) == 0
        validations['valid_hierarchy'] = parsed_data.get('heading_structure_valid', False)
        
        # Densidade (não muito poucas, não muitas)
        # 🆕 Usa densidade real se disponível
        if parsed_data.get('heading_density_source') == 'real':
            density = parsed_data.get('heading_density_real', 0)
        else:
            density = parsed_data.get('heading_density_estimate', 0)
        
        validations['optimal_density'] = 1 <= density <= 5  # 1-5 headings por 100 palavras
        
        # Score geral
        score_items = [
            validations['has_single_h1'],
            validations['h1_not_empty'],
            validations['h1_optimal_length'],
            validations['has_h2_structure'],
            validations['no_empty_headings'],
            validations['no_hidden_headings'],
            validations['valid_hierarchy']
        ]
        
        validations['heading_best_practices_score'] = int((sum(score_items) / len(score_items)) * 100)
        
        return validations
    
    def update_with_word_count(self, parsed_data: Dict[str, Any], word_count: int) -> Dict[str, Any]:
        """
        🆕 Atualiza dados parseados com word count real (para usar após content_parser)
        
        Args:
            parsed_data: Dados já parseados
            word_count: Word count real da página
            
        Returns:
            Dict com densidade real calculada
        """
        total_headings = parsed_data.get('total_headings_count', 0)
        
        if total_headings > 0 and word_count > 0:
            parsed_data['heading_density_real'] = (total_headings / word_count) * 100
            parsed_data['heading_density_source'] = 'real'
            
            # Recalcula validações com densidade real
            validations = self.validate_heading_best_practices(parsed_data)
            parsed_data.update(validations)
        
        return parsed_data

# ==========================================
# FUNÇÃO STANDALONE PARA TESTES
# ==========================================

def parse_headings_elements(html_content: str) -> Dict[str, Any]:
    """
    Função standalone para testar o HeadingsParser
    
    Args:
        html_content: HTML da página
        
    Returns:
        Dict com dados de headings parseados
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'lxml')
    parser = HeadingsParser()
    
    # Parse básico
    data = parser.parse(soup)
    
    # Adiciona análises extras
    data.update(parser.get_heading_summary(data))
    data.update(parser.validate_heading_best_practices(data))
    
    return data

# ==========================================
# EXEMPLO DE USO E TESTE
# ==========================================

if __name__ == "__main__":
    # Teste com HTML complexo incluindo problemas
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Teste Headings</title>
    </head>
    <body>
        <h1>Título Principal da Página</h1>
        
        <h2>Seção Importante</h2>
        <p>Conteúdo da seção...</p>
        
        <h3>Subseção</h3>
        
        <!-- Heading vazia (problema) -->
        <h2></h2>
        
        <!-- Heading escondida (suspeito) -->
        <h1 style="display: none;">Heading SEO Escondida</h1>
        
        <!-- Heading com apenas espaço -->
        <h3>&nbsp;</h3>
        
        <!-- Heading com class suspeita -->
        <h2 class="hidden">Texto Escondido</h2>
        
        <h4>Subseção nível 4</h4>
        <h5>Subseção nível 5</h5>
        
        <!-- Múltiplos H1 (problema) -->
        <h1>Segundo H1 - Problemático</h1>
        
    </body>
    </html>
    """
    
    # Parse e resultado
    result = parse_headings_elements(test_html)
    
    print("🔍 RESULTADO DO HEADINGS PARSER REFATORADO:")
    print(f"   H1 Count: {result['h1_count']} (Single: {result['single_h1']})")
    print(f"   H1 Text: '{result['h1_text']}'")
    print(f"   H2 Count: {result['h2_count']}")
    print(f"   H3 Count: {result['h3_count']}")
    print(f"   Total Headings: {result['total_headings_count']}")
    print(f"   Empty Headings: {result['empty_headings_count']}")
    print(f"   Hidden Headings: {result['hidden_headings_count']}")
    print(f"   Structure Valid: {result['heading_structure_valid']}")
    print(f"   Structure Score: {result['heading_structure_score']}/100")
    print(f"   Best Practices Score: {result['heading_best_practices_score']}/100")
    # 🆕 Severity information
    print(f"   Severity Level: {result['heading_severity_level']}")
    
    if result['heading_problems_list']:
        print(f"   Problemas encontrados:")
        for problem in result['heading_problems_list']:
            print(f"      - {problem}")
    
    # 🆕 Problems by severity
    if result['heading_problems_by_severity']:
        for severity, problems in result['heading_problems_by_severity'].items():
            if problems:
                print(f"   Problemas {severity}: {len(problems)}")
    
    if result['empty_headings_details']:
        print(f"   Headings vazias:")
        for empty in result['empty_headings_details']:
            print(f"      - {empty['level']}: {empty['reason']}")
    
    if result['hidden_headings_details']:
        print(f"   Headings escondidas:")
        for hidden in result['hidden_headings_details']:
            print(f"      - {hidden['level']}: {hidden['css_issue']}")