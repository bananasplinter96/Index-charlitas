#!/usr/bin/env python3
"""
procesar_exportacion.py

Script de procesamiento y estructuracion de base de conocimiento a partir
del historial exportado de Discord (exportacion_index.json).

Automatiza:
- Extraccion precisa de enlaces (tanto markdown [Titulo](URL) como URLs directas).
- Recuperacion de contexto y titulos desde mensajes, embeds o web scraping (BeautifulSoup).
- Clasificacion inteligente en al menos 4 categorias tecnicas.
- Generacion automatica de la estructura de repositorio:
    index-knowledge-base/
      |-- README.md
      |-- CONTRIBUTING.md
      `-- docs/
           |-- desarrollo.md
           |-- servidores.md
           |-- qa_testing.md
           `-- utilidades.md
"""

import json
import os
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# Rutas de entrada y salida
INPUT_JSON = Path("exportacion_index.json")
OUTPUT_DIR = Path("index-knowledge-base")
DOCS_DIR = OUTPUT_DIR / "docs"

# Expresiones regulares
URL_PATTERN = re.compile(r'https?://[^\s<>"]+')
MD_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\((https?://[^\s\)]+)\)')

# Headers HTTP para scraping
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

# Categorias y palabras clave
CATEGORIES = {
    "desarrollo": {
        "title": "Desarrollo de Software y Programacion",
        "file": "desarrollo.md",
        "description": "Librerias, frameworks, lenguajes, APIs, motores de videojuegos y repositorios de codigo.",
        "keywords": [
            "github", "gitlab", "code", "dev", "api", "python", "javascript", "typescript",
            "react", "vue", "angular", "rust", "golang", "c#", "dotnet", "backend", "frontend",
            "framework", "npm", "pypi", "stackoverflow", "programming", "git", "algoritmo",
            "sdk", "css", "html", "webdev", "godot", "unity", "uefn", "verse", "decomp", "recomp"
        ],
        "items": []
    },
    "servidores": {
        "title": "Servidores, DevOps e Infraestructura",
        "file": "servidores.md",
        "description": "Sistemas operativos, contenedores, nube (OCI/AWS), redes privadas, VPNs y homelab.",
        "keywords": [
            "server", "servidor", "docker", "kubernetes", "k8s", "aws", "azure", "gcp", "cloud",
            "oci", "oracle", "linux", "ubuntu", "debian", "vps", "nginx", "apache", "database",
            "sql", "postgres", "mysql", "redis", "devops", "hosting", "dns", "ssh", "bash",
            "deploy", "ci/cd", "jellyfin", "zerotier", "radmin", "hamachi", "selfhosted", "vm"
        ],
        "items": []
    },
    "qa_testing": {
        "title": "QA, Testing y Certificaciones",
        "file": "qa_testing.md",
        "description": "Aseguramiento de calidad, testing automatizado, certificaciones (ISTQB) y ciberseguridad.",
        "keywords": [
            "qa", "test", "testing", "cypress", "selenium", "jest", "playwright", "unit",
            "integration", "bug", "seguridad", "security", "pentest", "vulnerability", "cve",
            "audit", "benchmark", "quality", "check", "scanner", "istqb", "pruebas", "certificacion"
        ],
        "items": []
    },
    "utilidades": {
        "title": "Utilidades, Herramientas y Productividad",
        "file": "utilidades.md",
        "description": "Herramientas de automatizacion, descargadores, scripts, IA/LLMs y recursos multimedia.",
        "keywords": [
            "tool", "utility", "utilidad", "converter", "generator", "regex", "cheat",
            "cheatsheet", "icon", "font", "design", "figma", "calculator", "compressor",
            "online", "extension", "format", "free", "resource", "pdf", "image", "editor",
            "ai", "ia", "chatgpt", "gemini", "prompt", "llm", "llama", "huggingface", "dlp",
            "downloader", "scripts", "playnite", "achievement", "remote", "jobs"
        ],
        "items": []
    }
}


def clean_url(url: str) -> str:
    """Limpia caracteres de cierre residuales al final de una URL."""
    return url.rstrip(".,;:)>]*\"'")


def scrape_page_title(url: str) -> str:
    """Extrae el titulo <title> de la pagina web via BeautifulSoup."""
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=4, allow_redirects=True)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
                title = re.sub(r'\s+', ' ', title)
                if title:
                    return title
    except Exception:
        pass
    
    parsed = urllib.parse.urlparse(url)
    fallback = parsed.netloc + parsed.path.rstrip('/')
    return fallback if fallback else url


def classify_link(text_corpus: str) -> str:
    """Clasifica el enlace en una de las 4 categorias basandose en palabras clave."""
    corpus_lower = text_corpus.lower()
    scores = {}
    for cat_key, cat_data in CATEGORIES.items():
        score = sum(1 for kw in cat_data["keywords"] if kw in corpus_lower)
        scores[cat_key] = score
    
    best_cat = max(scores, key=scores.get)
    if scores[best_cat] > 0:
        return best_cat
    return "utilidades"


def process_export():
    if not INPUT_JSON.exists():
        print(f"[-] Error: Archivo {INPUT_JSON} no encontrado.")
        return

    print(f"[*] Leyendo historial desde {INPUT_JSON}...")
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = data.get("messages", [])
    print(f"[*] Total de mensajes procesados: {len(messages)}")

    candidates = []
    seen_urls = set()

    for msg in messages:
        content = msg.get("content", "") or ""
        embeds = msg.get("embeds", []) or []

        # Procesar linea por linea para respetar formatos estructurados de listas
        lines = content.splitlines() if content else [""]
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # 1. Buscar markdown links [Titulo](URL)
            md_matches = MD_LINK_PATTERN.findall(line_str)
            for title_match, raw_url in md_matches:
                url = clean_url(raw_url)
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                # Extraer texto restante de la linea como descripcion
                clean_title = re.sub(r'[*_~`]', '', title_match).strip()
                rest = line_str.replace(f"[{title_match}]({raw_url})", "")
                rest = re.sub(r'^[\s*#\-:—|]+', '', rest)
                rest = re.sub(r'[\s*#\-:—|]+$', '', rest).strip()

                candidates.append({
                    "url": url,
                    "tema": clean_title,
                    "descripcion": rest,
                    "needs_scrape": False
                })

            # 2. Buscar URLs directas que no esten ya capturadas en markdown link
            raw_urls = URL_PATTERN.findall(line_str)
            for raw_u in raw_urls:
                u = clean_url(raw_u)
                if not u or u in seen_urls:
                    continue
                seen_urls.add(u)

                # Contexto de la linea o del mensaje
                rest = line_str.replace(raw_u, "").strip()
                rest = re.sub(r'^[\s*#\-:—|]+', '', rest)
                rest = re.sub(r'[\s*#\-:—|]+$', '', rest).strip()

                # Buscar en embeds
                emb_title = None
                emb_desc = None
                for emb in embeds:
                    eu = emb.get("url") or ""
                    if eu and (eu in u or u in eu):
                        emb_title = emb.get("title")
                        emb_desc = emb.get("description")
                        break

                needs_scrape = False
                tema = emb_title or ""
                desc = rest or emb_desc or ""

                if not tema and not desc:
                    needs_scrape = True

                candidates.append({
                    "url": u,
                    "tema": tema,
                    "descripcion": desc,
                    "needs_scrape": needs_scrape
                })

    print(f"[*] Total de enlaces unicos detectados: {len(candidates)}")

    # Scraping concurrente con BeautifulSoup para los que no tienen texto ni titulo
    to_scrape = [c["url"] for c in candidates if c["needs_scrape"]]
    scraped_map = {}
    if to_scrape:
        print(f"[*] Extrayendo titulos faltantes via web scraping con BeautifulSoup ({len(to_scrape)} enlaces)...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(scrape_page_title, u): u for u in to_scrape}
            for fut in as_completed(future_to_url):
                u = future_to_url[fut]
                try:
                    scraped_map[u] = fut.result()
                except Exception:
                    scraped_map[u] = urllib.parse.urlparse(u).netloc

    # Ensamblar y clasificar
    for c in candidates:
        url = c["url"]
        tema = c["tema"]
        desc = c["descripcion"]

        if not tema:
            tema = scraped_map.get(url) or scrape_page_title(url)
        if not desc:
            desc = f"Recurso web extraido de {urllib.parse.urlparse(url).netloc}"

        # Limpiar caracteres que rompen el formato de tabla Markdown
        tema = re.sub(r'[\r\n|]', ' ', tema).strip()
        desc = re.sub(r'[\r\n|]', ' ', desc).strip()

        # Normalizar longitudes para tablas legibles
        if len(tema) > 75:
            tema = tema[:72] + "..."
        if len(desc) > 150:
            desc = desc[:147] + "..."

        corpus = f"{url} {tema} {desc}"
        cat_key = classify_link(corpus)

        CATEGORIES[cat_key]["items"].append({
            "tema": tema or "Recurso",
            "descripcion": desc or "Sin descripcion disponible",
            "url": url
        })

    # Imprimir resumen de clasificacion
    print("\n[+] Clasificacion final por categorias:")
    total_indexed = sum(len(c["items"]) for c in CATEGORIES.values())
    for cat_key, cat_data in CATEGORIES.items():
        print(f"    - {cat_data['title']}: {len(cat_data['items'])} enlaces")

    # Crear directorios
    OUTPUT_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Generar archivos por categoria en /docs
    for cat_key, cat_data in CATEGORIES.items():
        doc_path = DOCS_DIR / cat_data["file"]
        items = cat_data["items"]

        md_content = [
            f"# {cat_data['title']}\n",
            f"> {cat_data['description']}\n",
            f"Total de recursos indexados: **{len(items)}**\n",
            "| Tema/Nombre | Descripción | Enlace |",
            "| :--- | :--- | :--- |"
        ]

        if items:
            for it in items:
                link_md = f"[{it['url']}]({it['url']})"
                md_content.append(f"| {it['tema']} | {it['descripcion']} | {link_md} |")
        else:
            md_content.append("| *Sin registros* | *Sin enlaces actualmente* | - |")

        md_content.append("\n---\n*Generado automaticamente por el script de indexacion.*")

        with open(doc_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_content) + "\n")

    # 2. Generar README.md
    readme_path = OUTPUT_DIR / "README.md"
    readme_lines = [
        "# Index Knowledge Base 📚\n",
        "Bienvenido a la **Base de Conocimiento Centralizada**, construida a partir de los recursos, enlaces y herramientas recopilados en Discord.\n",
        "Este repositorio organiza enlaces tecnicos en categorias claras para consulta rapida y referencia del equipo.\n",
        "## 📁 Categorías y Documentación\n",
        "Explora los recursos organizados dentro de [`/docs`](./docs):\n",
        "| Categoría | Descripción | Archivo | Cantidad |",
        "| :--- | :--- | :--- | :--- |"
    ]

    for cat_key, cat_data in CATEGORIES.items():
        count = len(cat_data["items"])
        rel_path = f"./docs/{cat_data['file']}"
        readme_lines.append(f"| **{cat_data['title']}** | {cat_data['description']} | [{cat_data['file']}]({rel_path}) | {count} |")

    readme_lines.extend([
        f"\n**Total global de enlaces recopilados:** {total_indexed}\n",
        "## 🤝 Cómo Contribuir",
        "Para agregar nuevos enlaces o sugerir correcciones, consulta las normas y formato en [CONTRIBUTING.md](./CONTRIBUTING.md).\n",
        "## 🛠 Automatización",
        "Generado automaticamente mediante extraccion CLI con **DiscordChatExporter** y procesamiento con **Python (BeautifulSoup)**."
    ])

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(readme_lines) + "\n")

    # 3. Generar CONTRIBUTING.md
    contributing_path = OUTPUT_DIR / "CONTRIBUTING.md"
    contributing_content = """# Guía de Contribución 🤝

¡Gracias por tu interés en aportar a la **Index Knowledge Base**! Para garantizar la coherencia y calidad de la documentación, requerimos seguir este protocolo estricto.

## 📋 Reglas Generales

1. **Enlaces activos**: Verifica previamente que la URL responda correctamente (código HTTP 200).
2. **Sin duplicados**: Busca en [`/docs/`](./docs) antes de proponer un nuevo enlace.
3. **Clasificación adecuada**:
   - `docs/desarrollo.md`: Programación, frameworks, librerías, APIs y repositorios.
   - `docs/servidores.md`: Docker, Kubernetes, Linux, Cloud, VPS, bases de datos y redes.
   - `docs/qa_testing.md`: Testing, frameworks de pruebas, QA, certificaciones y ciberseguridad.
   - `docs/utilidades.md`: Herramientas online, generadores, conversores y productividad.

## 📐 Formato Estricto de Filas en Tablas

Cada aporte debe respetar el formato Markdown de 3 columnas:

```markdown
| Tema/Nombre | Descripción | Enlace |
| :--- | :--- | :--- |
| Nombre de la herramienta | Breve descripción de qué hace o por qué es útil | [https://ejemplo.com](https://ejemplo.com) |
```

### Especificaciones:
- **Tema/Nombre**: Título conciso del recurso o proyecto.
- **Descripción**: Resumen claro en 1 o 2 oraciones. No dejar en blanco ni repetir el nombre.
- **Enlace**: Siempre en formato markdown `[URL](URL)`.

## 🔄 Flujo de Trabajo (Git / Pull Requests)

1. Haz un Fork de este repositorio.
2. Crea una rama descriptiva:
   ```bash
   git checkout -b feature/recurso-nuevo
   ```
3. Añade la fila correspondiente en el archivo de categoría en `docs/`.
4. Haz commit respetando Conventional Commits:
   ```bash
   git commit -m "docs: agregar recurso de testing en qa_testing.md"
   ```
5. Abre un Pull Request describiendo tu aporte.
"""
    with open(contributing_path, "w", encoding="utf-8") as f:
        f.write(contributing_content)

    print(f"\n[OK] Repositorio generado con exito en: {OUTPUT_DIR.resolve()}")
    print("    |-- README.md")
    print("    |-- CONTRIBUTING.md")
    print("    `-- docs/")
    for cat_data in CATEGORIES.values():
        print(f"         |-- {cat_data['file']} ({len(cat_data['items'])} items)")


if __name__ == "__main__":
    process_export()
