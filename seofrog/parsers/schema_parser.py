"""
seofrog/parsers/schema_parser.py
Parser modular para análise completa de Structured Data
Responsável por: JSON-LD, Microdata, RDFa, Schema.org validation
"""

import json
import re
from typing import Dict, Any, List, Optional, Set
from bs4 import BeautifulSoup, Tag
from .base import ParserMixin, SeverityLevel

class SchemaParser(ParserMixin):
    """
    Parser especializado para análise completa de Structured Data
    Responsável por: JSON-LD, Microdata, RDFa, Schema.org types, validation
    """
    
    def __init__(self):
        super().__init__()
        
        # Schema.org types comuns que devemos procurar
        self.important_schema_types = {
            # Business
            'Organization', 'LocalBusiness', 'Corporation', 'NGO',
            'GovernmentOrganization', 'EducationalOrganization',
            
            # Content
            'Article', 'NewsArticle', 'BlogPosting', 'WebPage',
            'Product', 'Offer', 'Review', 'Rating',
            
            # Person & Social
            'Person', 'ContactPoint', 'PostalAddress',
            
            # Events & Places
            'Event', 'Place', 'Restaurant', 'Store',
            
            # Tech & SEO
            'WebSite', 'BreadcrumbList', 'SearchAction',
            'SiteNavigationElement', 'WPHeader', 'WPFooter',
            
            # FAQ & HowTo
            'FAQPage', 'Question', 'Answer', 'HowTo', 'HowToStep'
        }
        
        # Propriedades críticas por tipo
        self.critical_properties = {
            'Organization': ['name', 'url'],
            'LocalBusiness': ['name', 'address', 'telephone'],
            'Product': ['name', 'description', 'offers'],
            'Article': ['headline', 'author', 'datePublished'],
            'Review': ['reviewBody', 'author', 'reviewRating'],
            'BreadcrumbList': ['itemListElement'],
            'WebSite': ['name', 'url'],
            'FAQPage': ['mainEntity'],
            'HowTo': ['name', 'step']
        }
    
    def parse(self, soup: BeautifulSoup, url: str = None) -> Dict[str, Any]:
        """
        Parse completo de análise de structured data
        
        Args:
            soup: BeautifulSoup object da página
            url: URL da página (para validação de URLs no schema)
            
        Returns:
            Dict com dados completos de structured data
        """
        data = {}
        
        try:
            # Parse de cada tipo de structured data
            self._parse_json_ld(soup, data)
            self._parse_microdata(soup, data)
            self._parse_rdfa(soup, data)
            
            # Análise consolidada
            self._analyze_schema_coverage(data)
            self._analyze_schema_quality(data, url)
            
            # Detecção de problemas
            self._detect_schema_issues(data)
            
            # Severity scoring
            self._calculate_schema_severity(data)
            
            # Log estatísticas
            errors = 1 if any(key.endswith('_error') for key in data.keys()) else 0
            self.log_parsing_stats('SchemaParser', len(data), errors)
            
        except Exception as e:
            self.logger.error(f"Erro no parse de schema: {e}")
            data['schema_parse_error'] = str(e)
            self.log_parsing_stats('SchemaParser', len(data), 1)
        
        return data
    
    def _parse_json_ld(self, soup: BeautifulSoup, data: Dict):
        """
        Parse detalhado de JSON-LD schemas
        """
        json_ld_scripts = self.safe_find_all(soup, 'script', {'type': 'application/ld+json'})
        
        data['schema_json_ld_count'] = len(json_ld_scripts)
        data['json_ld_details'] = []
        data['json_ld_types'] = []
        data['json_ld_errors'] = []
        
        if not json_ld_scripts:
            return
        
        for i, script in enumerate(json_ld_scripts):
            script_text = self.extract_text_safe(script)
            
            try:
                # Parse JSON
                schema_data = json.loads(script_text)
                
                # Analisa o schema parseado
                schema_info = self._analyze_json_ld_schema(schema_data, i + 1)
                data['json_ld_details'].append(schema_info)
                
                # Coleta tipos encontrados
                if schema_info.get('types'):
                    data['json_ld_types'].extend(schema_info['types'])
                
            except json.JSONDecodeError as e:
                error_info = {
                    'script_index': i + 1,
                    'error': f'JSON inválido: {str(e)}',
                    'content_preview': script_text[:100] + '...' if len(script_text) > 100 else script_text
                }
                data['json_ld_errors'].append(error_info)
                self.logger.debug(f"JSON-LD inválido encontrado: {e}")
            
            except Exception as e:
                error_info = {
                    'script_index': i + 1,
                    'error': f'Erro no parse: {str(e)}',
                    'content_preview': script_text[:100] + '...' if len(script_text) > 100 else script_text
                }
                data['json_ld_errors'].append(error_info)
        
        # Remove duplicatas de tipos
        data['json_ld_types'] = list(set(data['json_ld_types']))
        data['json_ld_valid_count'] = len(data['json_ld_details'])
        data['json_ld_error_count'] = len(data['json_ld_errors'])
    
    def _analyze_json_ld_schema(self, schema_data: Any, script_index: int) -> Dict[str, Any]:
        """
        Analisa um schema JSON-LD individual
        """
        schema_info = {
            'script_index': script_index,
            'types': [],
            'properties': [],
            'has_context': False,
            'context_value': '',
            'is_valid_schema_org': False,
            'completeness_score': 0,
            'issues': []
        }
        
        try:
            # Normaliza para lista se necessário
            if isinstance(schema_data, dict):
                schemas = [schema_data]
            elif isinstance(schema_data, list):
                schemas = schema_data
            else:
                schema_info['issues'].append('Formato de schema inválido')
                return schema_info
            
            for schema in schemas:
                if not isinstance(schema, dict):
                    continue
                
                # Verifica @context
                context = schema.get('@context', '')
                if context:
                    schema_info['has_context'] = True
                    schema_info['context_value'] = str(context)
                    schema_info['is_valid_schema_org'] = 'schema.org' in str(context).lower()
                
                # Extrai @type
                schema_type = schema.get('@type', '')
                if schema_type:
                    if isinstance(schema_type, list):
                        schema_info['types'].extend(schema_type)
                    else:
                        schema_info['types'].append(schema_type)
                
                # Extrai propriedades
                properties = [key for key in schema.keys() if not key.startswith('@')]
                schema_info['properties'].extend(properties)
                
                # Verifica completude para tipos conhecidos
                if schema_type in self.critical_properties:
                    completeness = self._calculate_schema_completeness(schema, schema_type)
                    schema_info['completeness_score'] = max(schema_info['completeness_score'], completeness)
        
        except Exception as e:
            schema_info['issues'].append(f'Erro na análise: {str(e)}')
        
        # Remove duplicatas
        schema_info['types'] = list(set(schema_info['types']))
        schema_info['properties'] = list(set(schema_info['properties']))
        
        return schema_info
    
    def _calculate_schema_completeness(self, schema: Dict, schema_type: str) -> int:
        """
        Calcula score de completude (0-100) para um schema específico
        """
        critical_props = self.critical_properties.get(schema_type, [])
        if not critical_props:
            return 50  # Score neutro para tipos desconhecidos
        
        present_props = 0
        for prop in critical_props:
            if prop in schema and schema[prop]:
                present_props += 1
        
        return int((present_props / len(critical_props)) * 100)
    
    def _parse_microdata(self, soup: BeautifulSoup, data: Dict):
        """
        Parse detalhado de Microdata
        """
        # 🚀 CORRIGIDO: Adicionado parâmetro tag True
        microdata_items = self.safe_find_all(soup, True, attrs={'itemscope': True})
        
        data['schema_microdata_count'] = len(microdata_items)
        data['microdata_details'] = []
        data['microdata_types'] = []
        
        if not microdata_items:
            return
        
        for i, item in enumerate(microdata_items):
            microdata_info = {
                'item_index': i + 1,
                'itemtype': self.safe_get_attribute(item, 'itemtype'),
                'itemid': self.safe_get_attribute(item, 'itemid'),
                'properties': [],
                'tag_name': item.name,
                'is_schema_org': False
            }
            
            # Verifica se é schema.org
            itemtype = microdata_info['itemtype']
            if itemtype:
                microdata_info['is_schema_org'] = 'schema.org' in itemtype.lower()
                
                # Extrai tipo do schema
                if microdata_info['is_schema_org']:
                    type_name = itemtype.split('/')[-1]
                    data['microdata_types'].append(type_name)
            
            # Encontra propriedades (itemprop)
            properties = item.find_all(attrs={'itemprop': True})
            for prop in properties:
                prop_name = self.safe_get_attribute(prop, 'itemprop')
                prop_content = self._extract_microdata_content(prop)
                
                microdata_info['properties'].append({
                    'name': prop_name,
                    'content': prop_content[:100] + '...' if len(prop_content) > 100 else prop_content,
                    'tag': prop.name
                })
            
            data['microdata_details'].append(microdata_info)
        
        # Remove duplicatas de tipos
        data['microdata_types'] = list(set(data['microdata_types']))
    
    def _extract_microdata_content(self, element: Tag) -> str:
        """
        Extrai conteúdo de propriedade microdata
        """
        # Para diferentes tipos de elementos
        if element.name in ['meta']:
            return self.safe_get_attribute(element, 'content')
        elif element.name in ['img', 'audio', 'video']:
            return self.safe_get_attribute(element, 'src')
        elif element.name in ['a', 'link']:
            return self.safe_get_attribute(element, 'href')
        elif element.name in ['time']:
            return self.safe_get_attribute(element, 'datetime') or self.extract_text_safe(element)
        else:
            return self.extract_text_safe(element)
    
    def _parse_rdfa(self, soup: BeautifulSoup, data: Dict):
        """
        Parse detalhado de RDFa
        """
        # 🚀 CORRIGIDO: Adicionado parâmetro tag True
        rdfa_items = self.safe_find_all(soup, True, attrs={'typeof': True})
        
        data['schema_rdfa_count'] = len(rdfa_items)
        data['rdfa_details'] = []
        data['rdfa_types'] = []
        
        if not rdfa_items:
            return
        
        for i, item in enumerate(rdfa_items):
            rdfa_info = {
                'item_index': i + 1,
                'typeof': self.safe_get_attribute(item, 'typeof'),
                'resource': self.safe_get_attribute(item, 'resource'),
                'about': self.safe_get_attribute(item, 'about'),
                'properties': [],
                'tag_name': item.name
            }
            
            # Extrai tipo
            typeof = rdfa_info['typeof']
            if typeof:
                data['rdfa_types'].append(typeof)
            
            # Encontra propriedades (property)
            properties = item.find_all(attrs={'property': True})
            for prop in properties:
                prop_name = self.safe_get_attribute(prop, 'property')
                prop_content = self.safe_get_attribute(prop, 'content') or self.extract_text_safe(prop)
                
                rdfa_info['properties'].append({
                    'name': prop_name,
                    'content': prop_content[:100] + '...' if len(prop_content) > 100 else prop_content
                })
            
            data['rdfa_details'].append(rdfa_info)
        
        # Remove duplicatas de tipos
        data['rdfa_types'] = list(set(data['rdfa_types']))
    
    def _analyze_schema_coverage(self, data: Dict):
        """
        Analisa cobertura geral de structured data
        """
        # Total de schemas
        total_count = (
            data.get('schema_json_ld_count', 0) + 
            data.get('schema_microdata_count', 0) + 
            data.get('schema_rdfa_count', 0)
        )
        data['schema_total_count'] = total_count
        
        # Todos os tipos encontrados
        all_types = []
        all_types.extend(data.get('json_ld_types', []))
        all_types.extend(data.get('microdata_types', []))
        all_types.extend(data.get('rdfa_types', []))
        
        unique_types = list(set(all_types))
        data['schema_unique_types'] = unique_types
        data['schema_unique_types_count'] = len(unique_types)
        
        # Verifica tipos importantes
        important_found = []
        for schema_type in unique_types:
            if schema_type in self.important_schema_types:
                important_found.append(schema_type)
        
        data['schema_important_types_found'] = important_found
        data['schema_important_types_count'] = len(important_found)
        
        # Coverage score
        if self.important_schema_types:
            coverage_score = (len(important_found) / len(self.important_schema_types)) * 100
            data['schema_coverage_score'] = min(100, int(coverage_score))
        else:
            data['schema_coverage_score'] = 0
    
    def _analyze_schema_quality(self, data: Dict, url: str = None):
        """
        Analisa qualidade dos schemas encontrados
        """
        quality_issues = []
        
        # Verifica JSON-LD errors
        json_ld_errors = data.get('json_ld_error_count', 0)
        if json_ld_errors > 0:
            quality_issues.append(f'{json_ld_errors} JSON-LD com erros de sintaxe')
        
        # Verifica se tem @context válido
        json_ld_details = data.get('json_ld_details', [])
        invalid_context = 0
        for detail in json_ld_details:
            if not detail.get('is_valid_schema_org', False):
                invalid_context += 1
        
        if invalid_context > 0:
            quality_issues.append(f'{invalid_context} schemas sem @context schema.org válido')
        
        # Verifica completude
        low_completeness = 0
        for detail in json_ld_details:
            if detail.get('completeness_score', 0) < 50:
                low_completeness += 1
        
        if low_completeness > 0:
            quality_issues.append(f'{low_completeness} schemas com baixa completude')
        
        # Score geral de qualidade
        quality_factors = [
            data.get('schema_total_count', 0) > 0,          # Tem schemas
            json_ld_errors == 0,                            # Sem erros JSON
            invalid_context == 0,                           # Context válido
            data.get('schema_important_types_count', 0) > 0, # Tipos importantes
            low_completeness == 0                           # Boa completude
        ]
        
        data['schema_quality_score'] = int((sum(quality_factors) / len(quality_factors)) * 100)
        data['schema_quality_issues'] = quality_issues
        data['schema_quality_issues_count'] = len(quality_issues)
    
    def _detect_schema_issues(self, data: Dict):
        """
        Detecta problemas comuns de structured data
        """
        issues = []
        
        # Sem structured data
        if data.get('schema_total_count', 0) == 0:
            issues.append('sem_structured_data')
        
        # Erros de sintaxe JSON-LD
        if data.get('json_ld_error_count', 0) > 0:
            issues.append('json_ld_com_erros')
        
        # Baixa qualidade
        if data.get('schema_quality_score', 0) < 50:
            issues.append('baixa_qualidade_schema')
        
        # Poucos tipos importantes
        if data.get('schema_important_types_count', 0) == 0:
            issues.append('sem_tipos_importantes')
        
        # Baixa cobertura
        if data.get('schema_coverage_score', 0) < 25:
            issues.append('baixa_cobertura_schema')
        
        data['schema_issues'] = issues
        data['schema_issues_count'] = len(issues)
    
    def _calculate_schema_severity(self, data: Dict):
        """
        Calcula severity score para problemas de structured data
        """
        issues = data.get('schema_issues', [])
        
        # Mapeia issues para chaves de severity
        severity_issues = []
        for issue in issues:
            if issue == 'sem_structured_data':
                severity_issues.append('sem_structured_data')
            elif issue == 'json_ld_com_erros':
                severity_issues.append('structured_data_com_erros')
            elif issue in ['baixa_qualidade_schema', 'sem_tipos_importantes']:
                severity_issues.append('structured_data_baixa_qualidade')
            else:
                severity_issues.append('structured_data_incompleto')
        
        # Calcula severidade geral
        data['schema_severity_level'] = self.calculate_problem_severity(severity_issues)
        data['schema_problems_keys'] = severity_issues
        data['schema_problems_by_severity'] = self.categorize_problems_by_severity(severity_issues)
    
    # ==========================================
    # MÉTODOS DE ANÁLISE E RELATÓRIOS
    # ==========================================
    
    def get_schema_summary(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera resumo da análise de structured data
        """
        return {
            'total_schemas': parsed_data.get('schema_total_count', 0),
            'json_ld_count': parsed_data.get('schema_json_ld_count', 0),
            'microdata_count': parsed_data.get('schema_microdata_count', 0),
            'rdfa_count': parsed_data.get('schema_rdfa_count', 0),
            'unique_types_count': parsed_data.get('schema_unique_types_count', 0),
            'important_types_found': parsed_data.get('schema_important_types_found', []),
            'quality_score': parsed_data.get('schema_quality_score', 0),
            'coverage_score': parsed_data.get('schema_coverage_score', 0),
            'schema_severity_level': parsed_data.get('schema_severity_level', SeverityLevel.BAIXA),
            'main_issues': parsed_data.get('schema_issues', [])[:3],
            'has_errors': parsed_data.get('json_ld_error_count', 0) > 0
        }
    
    def validate_schema_best_practices(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida boas práticas de structured data
        """
        validations = {}
        
        # Presença de structured data
        validations['has_structured_data'] = parsed_data.get('schema_total_count', 0) > 0
        
        # Usa JSON-LD (recomendado pelo Google)
        validations['uses_json_ld'] = parsed_data.get('schema_json_ld_count', 0) > 0
        
        # Sem erros de sintaxe
        validations['no_syntax_errors'] = parsed_data.get('json_ld_error_count', 0) == 0
        
        # Tem tipos importantes
        validations['has_important_types'] = parsed_data.get('schema_important_types_count', 0) > 0
        
        # Boa qualidade
        validations['good_quality'] = parsed_data.get('schema_quality_score', 0) >= 70
        
        # Boa cobertura
        validations['good_coverage'] = parsed_data.get('schema_coverage_score', 0) >= 50
        
        # Sem problemas críticos
        validations['no_critical_issues'] = parsed_data.get('schema_severity_level') != SeverityLevel.CRITICA
        
        # Score geral
        score_items = [
            validations['has_structured_data'],
            validations['uses_json_ld'],
            validations['no_syntax_errors'],
            validations['has_important_types'],
            validations['good_quality'],
            validations['no_critical_issues']
        ]
        
        validations['schema_best_practices_score'] = int((sum(score_items) / len(score_items)) * 100)
        
        return validations

# ==========================================
# FUNÇÃO STANDALONE PARA TESTES
# ==========================================

def parse_schema_elements(html_content: str, url: str = 'https://example.com') -> Dict[str, Any]:
    """
    Função standalone para testar o SchemaParser
    
    Args:
        html_content: HTML da página
        url: URL da página (para validação)
        
    Returns:
        Dict com dados de structured data parseados
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'lxml')
    parser = SchemaParser()
    
    # Parse básico
    data = parser.parse(soup, url)
    
    # Adiciona análises extras
    data.update(parser.get_schema_summary(data))
    data.update(parser.validate_schema_best_practices(data))
    
    return data

# ==========================================
# EXEMPLO DE USO E TESTE
# ==========================================

if __name__ == "__main__":
    # Teste com HTML com diversos tipos de structured data
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Teste Schema.org</title>
        
        <!-- JSON-LD válido -->
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Empresa Teste",
            "url": "https://example.com",
            "logo": "https://example.com/logo.png",
            "contactPoint": {
                "@type": "ContactPoint",
                "telephone": "+55-11-1234-5678",
                "contactType": "customer service"
            }
        }
        </script>
        
        <!-- JSON-LD com erro de sintaxe -->
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Produto Teste",
            "description": "Descrição do produto"
            // Comentário inválido em JSON
        }
        </script>
        
        <!-- JSON-LD válido mas incompleto -->
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "Artigo de Teste"
        }
        </script>
        
    </head>
    <body>
        <!-- Microdata -->
        <div itemscope itemtype="https://schema.org/LocalBusiness">
            <h1 itemprop="name">Negócio Local</h1>
            <div itemprop="address" itemscope itemtype="https://schema.org/PostalAddress">
                <span itemprop="streetAddress">Rua Teste, 123</span>
                <span itemprop="addressLocality">São Paulo</span>
            </div>
            <span itemprop="telephone">11-1234-5678</span>
        </div>
        
        <!-- RDFa -->
        <div typeof="schema:Person">
            <span property="schema:name">João Silva</span>
            <span property="schema:jobTitle">Desenvolvedor</span>
        </div>
        
        <!-- Breadcrumbs -->
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Home",
                    "item": "https://example.com"
                },
                {
                    "@type": "ListItem", 
                    "position": 2,
                    "name": "Produtos",
                    "item": "https://example.com/produtos"
                }
            ]
        }
        </script>
        
    </body>
    </html>
    """
    
    # Parse e resultado
    result = parse_schema_elements(test_html)
    
    print("🔍 RESULTADO DO SCHEMA PARSER:")
    print(f"   Total Schemas: {result['total_schemas']}")
    print(f"   JSON-LD: {result['json_ld_count']} (válidos: {result.get('json_ld_valid_count', 0)})")
    print(f"   Microdata: {result['microdata_count']}")
    print(f"   RDFa: {result['rdfa_count']}")
    print(f"   Unique Types: {result['unique_types_count']} - {result.get('schema_unique_types', [])}")
    print(f"   Important Types: {result.get('schema_important_types_count', 0)} - {result['important_types_found']}")
    print(f"   Quality Score: {result['quality_score']}/100")
    print(f"   Coverage Score: {result['coverage_score']}/100")
    print(f"   Best Practices Score: {result['schema_best_practices_score']}/100")
    print(f"   Schema Severity: {result['schema_severity_level']}")
    
    if result.get('json_ld_error_count', 0) > 0:
        print(f"   ❌ JSON-LD Errors: {result['json_ld_error_count']}")
        for error in result.get('json_ld_errors', []):
            print(f"      Script {error['script_index']}: {error['error']}")
    
    if result['main_issues']:
        print(f"   Issues encontradas:")
        for issue in result['main_issues']:
            print(f"      - {issue}")
    
    if result.get('schema_quality_issues'):
        print(f"   Quality Issues:")
        for issue in result['schema_quality_issues']:
            print(f"      - {issue}")