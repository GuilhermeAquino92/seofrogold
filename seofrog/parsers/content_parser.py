"""
seofrog/parsers/content_parser.py
Parser modular para análise de conteúdo da página
Responsável por: word count, text ratio, thin content, readability
"""

import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup, Tag
from .base import ParserMixin, SeverityLevel

class ContentParser(ParserMixin):
    """
    Parser especializado para análise de conteúdo textual
    Responsável por: word count, character count, text ratio, thin content, readability
    """
    
    def __init__(self):
        super().__init__()
        
        # Configurações para análise de conteúdo
        self.min_word_count = 300      # Mínimo para não ser thin content
        self.ideal_word_count = 600    # Ideal para SEO
        self.max_word_count = 2500     # Máximo antes de ser muito longo
        
        # Tags que devem ser removidas do conteúdo textual
        self.excluded_tags = ['script', 'style', 'nav', 'header', 'footer', 'aside']
        
        # Seletores CSS para remover elementos não-principais
        self.excluded_selectors = [
            '.sidebar', '.menu', '.navigation', '.footer', '.header',
            '.advertisement', '.ads', '.social-share', '.comments'
        ]
    
    def parse(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Parse completo de análise de conteúdo
        
        Args:
            soup: BeautifulSoup object da página
            
        Returns:
            Dict com dados completos de conteúdo
        """
        data = {}
        
        try:
            # Extrai conteúdo principal limpo
            clean_soup = self._clean_content_for_analysis(soup)
            
            # Análise básica de texto
            self._analyze_basic_text_metrics(clean_soup, data)
            
            # Análise de qualidade do conteúdo
            self._analyze_content_quality(clean_soup, data)
            
            # Análise de estrutura (parágrafos, listas)
            self._analyze_content_structure(clean_soup, data)
            
            # Análise de readability básica
            self._analyze_readability(clean_soup, data)
            
            # Detecção de thin content e problemas
            self._detect_content_issues(data)
            
            # Severity scoring
            self._calculate_content_severity(data)
            
            # Log estatísticas
            errors = 1 if any(key.endswith('_error') for key in data.keys()) else 0
            self.log_parsing_stats('ContentParser', len(data), errors)
            
        except Exception as e:
            self.logger.error(f"Erro no parse de conteúdo: {e}")
            data['content_parse_error'] = str(e)
            self.log_parsing_stats('ContentParser', len(data), 1)
        
        return data
    
    def _clean_content_for_analysis(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        Remove elementos que não fazem parte do conteúdo principal
        
        Args:
            soup: BeautifulSoup original
            
        Returns:
            BeautifulSoup com conteúdo limpo para análise
        """
        # Cria cópia para não modificar o original
        clean_soup = BeautifulSoup(str(soup), 'lxml')
        
        # Remove tags que não são conteúdo principal
        for tag_name in self.excluded_tags:
            for tag in clean_soup.find_all(tag_name):
                tag.decompose()
        
        # Remove elementos por seletor CSS (se possível)
        try:
            for selector in self.excluded_selectors:
                for element in clean_soup.select(selector):
                    element.decompose()
        except Exception as e:
            self.logger.debug(f"Erro removendo seletores CSS: {e}")
        
        return clean_soup
    
    def _analyze_basic_text_metrics(self, clean_soup: BeautifulSoup, data: Dict):
        """
        Análise básica de métricas de texto
        """
        # Extrai todo o texto da página limpa
        full_text = self.extract_text_safe(clean_soup)
        
        # Métricas básicas
        data['full_text_content'] = full_text  # Para debug/análise (pode ser removido em produção)
        data['character_count'] = len(full_text)
        data['character_count_no_spaces'] = len(full_text.replace(' ', ''))
        
        # Word count usando regex mais preciso
        words = re.findall(r'\b\w+\b', full_text)
        data['word_count'] = len(words)
        
        # Contagem de frases (aproximada)
        sentences = re.split(r'[.!?]+', full_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        data['sentence_count'] = len(sentences)
        
        # Contagem de parágrafos (estimativa baseada em quebras duplas)
        paragraphs = re.split(r'\n\s*\n', full_text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        data['paragraph_count_estimate'] = len(paragraphs)
        
        # Text ratio (texto vs HTML total)
        html_length = len(str(clean_soup))
        data['text_ratio'] = len(full_text) / html_length if html_length > 0 else 0
        
        # Densidade de texto (caracteres por palavra)
        data['avg_chars_per_word'] = data['character_count'] / data['word_count'] if data['word_count'] > 0 else 0
        
        # Comprimento médio de frase
        data['avg_words_per_sentence'] = data['word_count'] / data['sentence_count'] if data['sentence_count'] > 0 else 0
    
    def _analyze_content_quality(self, clean_soup: BeautifulSoup, data: Dict):
        """
        Analisa qualidade e características do conteúdo
        """
        word_count = data.get('word_count', 0)
        
        # Classificação por comprimento
        data['content_length_category'] = self._classify_content_length(word_count)
        
        # Análise de thin content
        data['is_thin_content'] = word_count < self.min_word_count
        data['is_ideal_length'] = self.min_word_count <= word_count <= self.max_word_count
        data['is_too_long'] = word_count > self.max_word_count
        
        # Análise de densidade de palavras únicas
        full_text = data.get('full_text_content', '')
        if full_text:
            words = re.findall(r'\b\w+\b', full_text.lower())
            unique_words = set(words)
            data['unique_words_count'] = len(unique_words)
            data['word_diversity_ratio'] = len(unique_words) / len(words) if words else 0
        else:
            data['unique_words_count'] = 0
            data['word_diversity_ratio'] = 0
        
        # Detecção de conteúdo duplicado/repetitivo (básico)
        data['repetition_score'] = self._calculate_repetition_score(full_text)
    
    def _analyze_content_structure(self, clean_soup: BeautifulSoup, data: Dict):
        """
        Analisa estrutura do conteúdo (parágrafos, listas, etc.)
        """
        # Contagem real de parágrafos
        paragraphs = self.safe_find_all(clean_soup, 'p')
        data['paragraph_count'] = len(paragraphs)
        
        # Análise de parágrafos
        if paragraphs:
            paragraph_lengths = []
            for p in paragraphs:
                p_text = self.extract_text_safe(p)
                paragraph_lengths.append(len(p_text))
            
            data['avg_paragraph_length'] = sum(paragraph_lengths) / len(paragraph_lengths)
            data['longest_paragraph'] = max(paragraph_lengths) if paragraph_lengths else 0
            data['shortest_paragraph'] = min(paragraph_lengths) if paragraph_lengths else 0
        else:
            data['avg_paragraph_length'] = 0
            data['longest_paragraph'] = 0
            data['shortest_paragraph'] = 0
        
        # Contagem de listas
        ul_lists = self.safe_find_all(clean_soup, 'ul')
        ol_lists = self.safe_find_all(clean_soup, 'ol')
        data['unordered_lists_count'] = len(ul_lists)
        data['ordered_lists_count'] = len(ol_lists)
        data['total_lists_count'] = len(ul_lists) + len(ol_lists)
        
        # Contagem de itens de lista
        list_items = self.safe_find_all(clean_soup, 'li')
        data['list_items_count'] = len(list_items)
        
        # Elementos de formatação
        strong_tags = self.safe_find_all(clean_soup, 'strong')
        em_tags = self.safe_find_all(clean_soup, 'em')
        b_tags = self.safe_find_all(clean_soup, 'b')
        i_tags = self.safe_find_all(clean_soup, 'i')
        
        data['bold_elements_count'] = len(strong_tags) + len(b_tags)
        data['italic_elements_count'] = len(em_tags) + len(i_tags)
        data['formatting_elements_count'] = data['bold_elements_count'] + data['italic_elements_count']
    
    def _analyze_readability(self, clean_soup: BeautifulSoup, data: Dict):
        """
        Análise básica de readability (sem bibliotecas externas)
        """
        word_count = data.get('word_count', 0)
        sentence_count = data.get('sentence_count', 0)
        
        # Flesch Reading Ease simplificado (aproximação)
        if sentence_count > 0 and word_count > 0:
            avg_sentence_length = word_count / sentence_count
            
            # Estimativa de sílabas (aproximação: vogais)
            full_text = data.get('full_text_content', '')
            vowels = re.findall(r'[aeiouAEIOU]', full_text)
            estimated_syllables = len(vowels)
            avg_syllables_per_word = estimated_syllables / word_count if word_count > 0 else 0
            
            # Fórmula Flesch simplificada
            flesch_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
            flesch_score = max(0, min(100, flesch_score))  # Limita entre 0-100
            
            data['flesch_reading_ease'] = round(flesch_score, 1)
            data['readability_level'] = self._classify_readability(flesch_score)
        else:
            data['flesch_reading_ease'] = 0
            data['readability_level'] = 'unknown'
        
        # Outras métricas de readability
        data['avg_sentence_length'] = data.get('avg_words_per_sentence', 0)
        data['complex_sentences'] = len([s for s in re.split(r'[.!?]+', data.get('full_text_content', '')) 
                                       if len(s.split()) > 20])  # Frases com >20 palavras
    
    def _detect_content_issues(self, data: Dict):
        """
        Detecta problemas comuns de conteúdo
        """
        issues = []
        
        word_count = data.get('word_count', 0)
        
        # Thin content
        if word_count < self.min_word_count:
            if word_count < 100:
                issues.append('thin_content_critico')
            else:
                issues.append('thin_content')
        
        # Conteúdo muito longo
        if word_count > self.max_word_count:
            issues.append('content_muito_longo')
        
        # Baixa densidade de texto
        text_ratio = data.get('text_ratio', 0)
        if text_ratio < 0.1:  # Menos de 10% do HTML é texto
            issues.append('baixa_densidade_texto')
        
        # Parágrafos muito longos
        avg_paragraph = data.get('avg_paragraph_length', 0)
        if avg_paragraph > 200:
            issues.append('paragrafos_muito_longos')
        
        # Falta de estrutura
        paragraph_count = data.get('paragraph_count', 0)
        if paragraph_count < 3 and word_count > 300:
            issues.append('falta_estrutura_paragrafos')
        
        # Baixa diversidade de palavras (possível spam)
        diversity = data.get('word_diversity_ratio', 0)
        if diversity < 0.3:  # Menos de 30% palavras únicas
            issues.append('baixa_diversidade_palavras')
        
        # Alto score de repetição
        repetition = data.get('repetition_score', 0)
        if repetition > 0.7:
            issues.append('conteudo_repetitivo')
        
        data['content_issues'] = issues
        data['content_issues_count'] = len(issues)
    
    def _calculate_content_severity(self, data: Dict):
        """
        Calcula severity score para problemas de conteúdo
        """
        issues = data.get('content_issues', [])
        
        # Mapeia issues para chaves de severity
        severity_issues = []
        for issue in issues:
            if issue == 'thin_content_critico':
                severity_issues.append('thin_content_critico')
            elif issue == 'thin_content':
                severity_issues.append('thin_content')
            elif issue in ['baixa_densidade_texto', 'conteudo_repetitivo']:
                severity_issues.append('qualidade_conteudo_baixa')
            else:
                severity_issues.append('estrutura_conteudo_ruim')
        
        # Calcula severidade geral
        data['content_severity_level'] = self.calculate_problem_severity(severity_issues)
        data['content_problems_keys'] = severity_issues
        data['content_problems_by_severity'] = self.categorize_problems_by_severity(severity_issues)
    
    # ==========================================
    # MÉTODOS AUXILIARES
    # ==========================================
    
    def _classify_content_length(self, word_count: int) -> str:
        """Classifica conteúdo por comprimento"""
        if word_count < 100:
            return 'muito_curto'
        elif word_count < self.min_word_count:
            return 'curto'
        elif word_count <= self.ideal_word_count:
            return 'ideal'
        elif word_count <= self.max_word_count:
            return 'longo'
        else:
            return 'muito_longo'
    
    def _classify_readability(self, flesch_score: float) -> str:
        """Classifica nível de readability baseado no Flesch score"""
        if flesch_score >= 90:
            return 'muito_facil'
        elif flesch_score >= 80:
            return 'facil'
        elif flesch_score >= 70:
            return 'medio_facil'
        elif flesch_score >= 60:
            return 'medio'
        elif flesch_score >= 50:
            return 'medio_dificil'
        elif flesch_score >= 30:
            return 'dificil'
        else:
            return 'muito_dificil'
    
    def _calculate_repetition_score(self, text: str) -> float:
        """
        Calcula score de repetição do conteúdo (0-1)
        1 = muito repetitivo, 0 = pouco repetitivo
        """
        if not text or len(text) < 100:
            return 0
        
        # Analisa bigrams (pares de palavras consecutivas)
        words = re.findall(r'\b\w+\b', text.lower())
        if len(words) < 10:
            return 0
        
        bigrams = []
        for i in range(len(words) - 1):
            bigrams.append(f"{words[i]} {words[i+1]}")
        
        # Calcula repetição baseada em bigrams únicos
        unique_bigrams = set(bigrams)
        repetition_ratio = 1 - (len(unique_bigrams) / len(bigrams))
        
        return min(1.0, repetition_ratio * 2)  # Amplifica um pouco o score
    
    # ==========================================
    # MÉTODOS DE ANÁLISE E RELATÓRIOS
    # ==========================================
    
    def get_content_summary(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera resumo da análise de conteúdo
        
        Args:
            parsed_data: Dados já parseados
            
        Returns:
            Dict com resumo de análise
        """
        word_count = parsed_data.get('word_count', 0)
        issues = parsed_data.get('content_issues', [])
        
        return {
            'content_length_category': parsed_data.get('content_length_category', 'unknown'),
            'is_quality_content': word_count >= self.min_word_count and len(issues) <= 2,
            'readability_level': parsed_data.get('readability_level', 'unknown'),
            'content_severity_level': parsed_data.get('content_severity_level', SeverityLevel.BAIXA),
            'main_issues': issues[:3],  # Top 3 issues
            'word_count': word_count,
            'text_ratio': parsed_data.get('text_ratio', 0),
            'paragraph_count': parsed_data.get('paragraph_count', 0)
        }
    
    def validate_content_best_practices(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida boas práticas de conteúdo
        
        Args:
            parsed_data: Dados parseados
            
        Returns:
            Dict com validações
        """
        validations = {}
        
        word_count = parsed_data.get('word_count', 0)
        
        # Comprimento adequado
        validations['adequate_length'] = word_count >= self.min_word_count
        validations['not_too_long'] = word_count <= self.max_word_count
        validations['ideal_length'] = self.min_word_count <= word_count <= self.ideal_word_count
        
        # Qualidade estrutural
        validations['good_text_ratio'] = parsed_data.get('text_ratio', 0) >= 0.15
        validations['adequate_paragraphs'] = parsed_data.get('paragraph_count', 0) >= 3
        validations['good_readability'] = parsed_data.get('flesch_reading_ease', 0) >= 50
        
        # Diversidade e originalidade
        validations['good_word_diversity'] = parsed_data.get('word_diversity_ratio', 0) >= 0.4
        validations['low_repetition'] = parsed_data.get('repetition_score', 0) <= 0.5
        
        # Score geral
        score_items = [
            validations['adequate_length'],
            validations['not_too_long'],
            validations['good_text_ratio'],
            validations['adequate_paragraphs'],
            validations['good_readability'],
            validations['good_word_diversity'],
            validations['low_repetition']
        ]
        
        validations['content_best_practices_score'] = int((sum(score_items) / len(score_items)) * 100)
        
        return validations

# ==========================================
# FUNÇÃO STANDALONE PARA TESTES
# ==========================================

def parse_content_elements(html_content: str) -> Dict[str, Any]:
    """
    Função standalone para testar o ContentParser
    
    Args:
        html_content: HTML da página
        
    Returns:
        Dict com dados de conteúdo parseados
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'lxml')
    parser = ContentParser()
    
    # Parse básico
    data = parser.parse(soup)
    
    # Remove full_text_content para não poluir output de teste
    if 'full_text_content' in data:
        data['full_text_content'] = data['full_text_content'][:100] + '...' if len(data['full_text_content']) > 100 else data['full_text_content']
    
    # Adiciona análises extras
    data.update(parser.get_content_summary(data))
    data.update(parser.validate_content_best_practices(data))
    
    return data

# ==========================================
# EXEMPLO DE USO E TESTE
# ==========================================

if __name__ == "__main__":
    # Teste com HTML com conteúdo variado
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Teste de Conteúdo</title>
    </head>
    <body>
        <header>
            <nav>Menu de navegação que será removido</nav>
        </header>
        
        <main>
            <h1>Título Principal do Artigo</h1>
            
            <p>Este é o primeiro parágrafo do artigo. Contém informações importantes sobre o tópico 
            principal que estamos discutindo. O conteúdo deve ser relevante e informativo para os leitores.</p>
            
            <p>O segundo parágrafo continua a explicação. Aqui temos mais detalhes sobre o assunto,
            incluindo <strong>pontos importantes</strong> e <em>conceitos relevantes</em> que precisam
            ser destacados para melhor compreensão.</p>
            
            <h2>Seção com Lista</h2>
            
            <p>Esta seção apresenta informações em formato de lista:</p>
            
            <ul>
                <li>Primeiro item da lista com informações relevantes</li>
                <li>Segundo item explicando outros aspectos</li>
                <li>Terceiro item com conclusões importantes</li>
            </ul>
            
            <p>Parágrafo final que conclui o artigo. Aqui resumimos os pontos principais e 
            oferecemos uma perspectiva final sobre o tópico. Este conteúdo tem aproximadamente
            200 palavras para testar a análise de densidade e qualidade.</p>
            
        </main>
        
        <footer>
            <div class="social-share">Botões de compartilhamento</div>
        </footer>
        
        <script>
            // Este script será removido da análise
            console.log("Script que não faz parte do conteúdo");
        </script>
    </body>
    </html>
    """
    
    # Parse e resultado
    result = parse_content_elements(test_html)
    
    print("🔍 RESULTADO DO CONTENT PARSER:")
    print(f"   Word Count: {result['word_count']} palavras")
    print(f"   Character Count: {result['character_count']} caracteres")
    print(f"   Sentence Count: {result['sentence_count']} frases")
    print(f"   Paragraph Count: {result['paragraph_count']} parágrafos")
    print(f"   Text Ratio: {result['text_ratio']:.2%}")
    print(f"   Content Length Category: {result['content_length_category']}")
    print(f"   Is Quality Content: {result['is_quality_content']}")
    print(f"   Readability Level: {result['readability_level']}")
    print(f"   Flesch Score: {result['flesch_reading_ease']}")
    print(f"   Content Severity: {result['content_severity_level']}")
    print(f"   Best Practices Score: {result['content_best_practices_score']}/100")
    
    if result['content_issues']:
        print(f"   Issues encontradas:")
        for issue in result['content_issues']:
            print(f"      - {issue}")
    
    print(f"   Lists: {result['total_lists_count']} ({result['list_items_count']} items)")
    print(f"   Formatting: {result['formatting_elements_count']} elementos")
    print(f"   Word Diversity: {result['word_diversity_ratio']:.2%}")
    print(f"   Repetition Score: {result['repetition_score']:.2f}")