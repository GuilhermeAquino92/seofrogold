#!/usr/bin/env python3
"""
setup.py - SEOFrog v0.2 Enterprise Distribution Setup
Professional Screaming Frog Clone
"""

from setuptools import setup, find_packages
import pathlib
import re


setup(
    name="seofrog",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # aqui você pode listar suas dependências reais depois
    ],
    entry_points={
        'console_scripts': [
            'seofrog=seofrog.main:main',
        ],
    },
)

# === PATHS ===
HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text(encoding='utf-8') if (HERE / "README.md").exists() else "SEOFrog Enterprise - Professional Screaming Frog Clone"

# === VERSION EXTRACTION ===
def get_version():
    """Extrai versão do __init__.py"""
    init_file = HERE / "seofrog" / "__init__.py"
    if init_file.exists():
        content = init_file.read_text(encoding='utf-8')
        match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
    return "0.2.0"

VERSION = get_version()

# === REQUIREMENTS ===
CORE_REQUIREMENTS = [
    "requests>=2.31.0",
    "beautifulsoup4>=4.12.0", 
    "lxml>=4.9.0",
    "pandas>=2.0.0",
    "urllib3>=2.0.0",
]

CLI_REQUIREMENTS = [
    "click>=8.1.0",
    "rich>=13.0.0",
    "colorama>=0.4.6",
    "tqdm>=4.65.0",
]

VALIDATION_REQUIREMENTS = [
    "pydantic>=2.0.0",
    "validators>=0.20.0",
]

EXPORT_REQUIREMENTS = [
    "openpyxl>=3.1.0",
    "xlsxwriter>=3.1.0",
]

PERFORMANCE_REQUIREMENTS = [
    "psutil>=5.9.0",
    "aiohttp>=3.8.0",
]

# Optional advanced features
ADVANCED_REQUIREMENTS = [
    "selenium>=4.15.0",
    "playwright>=1.40.0", 
]

DEV_REQUIREMENTS = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
    "mypy>=1.5.0",
    "pre-commit>=3.4.0",
]

# === SETUP CONFIGURATION ===
setup(
    # === BASIC INFO ===
    name="seofrog",
    version=VERSION,
    description="Professional Screaming Frog Clone - Enterprise SEO Crawler",
    long_description=README,
    long_description_content_type="text/markdown",
    
    # === AUTHOR INFO ===
    author="SEOFrog Team",
    author_email="dev@seofrog.com",
    maintainer="SEOFrog Team",
    maintainer_email="dev@seofrog.com",
    
    # === URLS ===
    url="https://github.com/seofrog/seofrog",
    project_urls={
        "Homepage": "https://seofrog.com",
        "Documentation": "https://docs.seofrog.com",
        "Repository": "https://github.com/seofrog/seofrog",
        "Issues": "https://github.com/seofrog/seofrog/issues",
        "Changelog": "https://github.com/seofrog/seofrog/blob/main/CHANGELOG.md",
    },
    
    # === LICENSE ===
    license="MIT",
    
    # === CLASSIFIERS ===
    classifiers=[
        # Development Status
        "Development Status :: 4 - Beta",
        
        # Intended Audience
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Other Audience",
        
        # Topic
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Internet :: WWW/HTTP :: Site Management",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Monitoring",
        "Topic :: Utilities",
        
        # License
        "License :: OSI Approved :: MIT License",
        
        # Programming Language
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10", 
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        
        # Operating System
        "Operating System :: OS Independent",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        
        # Environment
        "Environment :: Console",
        "Environment :: Web Environment",
        
        # Natural Language
        "Natural Language :: English",
        "Natural Language :: Portuguese (Brazilian)",
    ],
    
    # === KEYWORDS ===
    keywords=[
        "seo", "crawler", "scraping", "web-scraping", "screaming-frog",
        "seo-tools", "website-analysis", "web-crawler", "seo-audit",
        "link-analysis", "meta-tags", "technical-seo", "site-audit"
    ],
    
    # === PYTHON REQUIREMENTS ===
    python_requires=">=3.9",
    
    # === PACKAGES ===
    packages=find_packages(
        exclude=["tests", "tests.*", "docs", "docs.*", "examples", "examples.*"]
    ),
    
    # === PACKAGE DATA ===
    include_package_data=True,
    package_data={
        "seofrog": [
            "data/*.json",
            "data/*.txt", 
            "templates/*.html",
            "static/*",
        ],
    },
    
    # === DEPENDENCIES ===
    install_requires=CORE_REQUIREMENTS + CLI_REQUIREMENTS + VALIDATION_REQUIREMENTS,
    
    # === OPTIONAL DEPENDENCIES ===
    extras_require={
        "full": CORE_REQUIREMENTS + CLI_REQUIREMENTS + VALIDATION_REQUIREMENTS + 
                EXPORT_REQUIREMENTS + PERFORMANCE_REQUIREMENTS,
        
        "export": EXPORT_REQUIREMENTS,
        
        "performance": PERFORMANCE_REQUIREMENTS,
        
        "advanced": ADVANCED_REQUIREMENTS,
        
        "dev": DEV_REQUIREMENTS,
        
        "all": CORE_REQUIREMENTS + CLI_REQUIREMENTS + VALIDATION_REQUIREMENTS +
               EXPORT_REQUIREMENTS + PERFORMANCE_REQUIREMENTS + ADVANCED_REQUIREMENTS + DEV_REQUIREMENTS,
    },
    
    # === ENTRY POINTS ===
    entry_points={
        "console_scripts": [
            "seofrog=seofrog.main:cli_entry_point",
            "seofrog-analyze=seofrog.analyzers.seo_analyzer:analyze_cli",
        ],
    },
    
    # === ZIP SAFE ===
    zip_safe=False,
    
    # === ADDITIONAL OPTIONS ===
    options={
        "bdist_wheel": {
            "universal": False,  # Not universal because we use Python 3.9+
        },
    },
)

# === POST-INSTALL MESSAGE ===
print("""
🐸 =====================================================
   SEOFrog v{version} Enterprise Installation Complete!
🐸 =====================================================

🚀 Quick Start:
   seofrog https://example.com
   seofrog https://example.com --profile deep
   seofrog --help

📚 Documentation:
   https://docs.seofrog.com

🔧 Advanced Installation:
   pip install seofrog[full]     # All features
   pip install seofrog[advanced] # JS rendering support
   pip install seofrog[dev]      # Development tools

🐛 Issues & Support:
   https://github.com/seofrog/seofrog/issues

Happy crawling! 🕷️
""".format(version=VERSION))