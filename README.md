<div align="center">

# Paper Visual Reader

**Transform academic papers into interactive, evidence-gated HTML digests**

[English](#english) | [中文](#中文) | [Español](#español)

<img src="https://img.shields.io/badge/version-4.0-blue" alt="version">
<img src="https://img.shields.io/badge/KaTeX-0.16.11-green" alt="katex">
<img src="https://img.shields.io/badge/license-MIT-yellow" alt="license">
<img src="https://img.shields.io/badge/templates-5-purple" alt="templates">

</div>

---

<a name="english"></a>

## What It Does

Paper Visual Reader converts PDF/LaTeX academic papers into standalone HTML digests that are **more informative than reading the original paper**. Every claim is traced to its source, every equation is rendered with KaTeX, and an anti-hallucination guard ensures nothing is fabricated.

### Features

- **Premium Academic Template**: Three-panel layout (sidebar TOC + main content + right margin panel) with Crimson Pro serif typography, dark/light theme toggle, and reading progress bar
- **5 Specialized Templates**: Premium Academic (default), Theory, Empirical, Review/Survey, Comparative
- **Evidence Gating**: Every claim has a severity tier (Strong / Moderate / Weak) with source anchors
- **Anti-Hallucination Guard**: Deterministic validator that blocks ungrounded claims before delivery
- **KaTeX Math Rendering**: Full LaTeX math support with auto-overflow protection
- **Interactive UI**: Section search/filter, notation glossary modal, smooth-scroll TOC with active tracking
- **Right Margin Panel**: At-a-glance stats, evidence quality meter, key notation quick-reference, dynamic section indicator

### Quick Start

```
paper-visual-reader /path/to/paper.pdf
```

Output:
```
paper_digest_<Author>_<Year>_<Title>/
├── digest.html                  # Interactive visual digest
├── evidence_ledger.json         # Claim-level source mapping
├── guard_report.md              # Anti-hallucination report
└── guard_report.json            # Machine-readable report
```

### Detail Levels

| Level | Word Count | Interpretation | Proofs |
|-------|-----------|----------------|--------|
| standard | 1/2 of source | Main results only | Sketch |
| **premium** (default) | 2/3 of source | All results | Strategy + key steps |
| deep | Full reproduction | All items | Full reproduction |

### Templates

| Template | Best For |
|----------|---------|
| `premium_academic` | General papers, default choice |
| `theory` | Papers with lemmas, theorems, proofs |
| `empirical` | Regression-heavy empirical work |
| `review` | Survey/review articles (Annual Reviews, JEL, Handbooks) |
| `comparative` | Side-by-side comparison of two papers |

### Architecture

```
INTAKE -> EXTRACT_TEXT -> AI ANALYSIS -> BUILD_EVIDENCE_LEDGER -> DRAFT_HTML -> RUN_GUARD
```

The AI agent reads the full paper, extracts all formal results, builds a claim-level evidence ledger, drafts the HTML digest, then validates everything through the anti-hallucination guard. If the guard returns FAIL, the agent iterates until PASS.

### Project Structure

```
paper-visual-reader/
├── SKILL.md                          # Skill specification
├── references/
│   ├── templates/
│   │   ├── premium_academic.html     # Default 3-panel template
│   │   ├── theory.html               # Theory paper template
│   │   ├── empirical.html            # Empirical paper template
│   │   ├── review.html               # Review/survey template
│   │   └── comparative.html          # Two-paper comparison
│   ├── paper_structure_guide.md      # Extraction granularity rules
│   ├── evidence_ledger_schema.md     # Ledger JSON schema
│   ├── anti_hallucination_module.md  # Guard specification
│   └── visual_output_templates.md    # Design goals
├── scripts/
│   ├── source_extractor.py           # PDF text extraction (pdftotext/fitz/OCR)
│   ├── anti_hallucination_guard.py   # Deterministic claim validator
│   ├── claim_builder.py              # Source-driven claim generation
│   └── run_fixtures.py               # Regression test suite
└── agents/
    └── openai.yaml                   # Agent configuration
```

### Premium Academic Template

The default template features a three-column layout optimized for wide screens:

- **Left sidebar** (280px): Sticky table of contents with active section tracking
- **Main content** (flex, max 860px): Paper sections, claim cards, equation blocks, interpretation boxes
- **Right panel** (260px): Paper stats, evidence quality meter, key contributions, notation quick-reference, dynamic section indicator

The right panel collapses at 1200px. Below 768px the layout switches to single-column mobile mode.

---

<a name="中文"></a>

## 功能介绍

Paper Visual Reader 将 PDF/LaTeX 学术论文转换为独立的 HTML 可视化摘要。产出的摘要**比直接读原文更有信息量**：每个论断都追溯到原文出处，每个公式都用 KaTeX 渲染，反幻觉守卫确保不会凭空捏造内容。

### 核心特性

- **Premium Academic 模板**：三栏布局（侧边栏目录 + 主内容区 + 右侧边注面板），Crimson Pro 衬线字体，明暗主题切换，阅读进度条
- **5 种专用模板**：Premium Academic（默认）、Theory、Empirical、Review/Survey、Comparative
- **证据分级**：每个论断标注严重程度（Strong / Moderate / Weak），附源文锚点
- **反幻觉守卫**：确定性验证器，在交付前拦截无依据的论断
- **KaTeX 数学渲染**：完整 LaTeX 公式支持，自动溢出保护
- **交互式界面**：章节搜索/过滤、符号表模态框、平滑滚动目录与活跃追踪
- **右侧边注面板**：论文速览信息、证据质量仪表、关键符号速查、动态章节指示器

### 快速开始

```
paper-visual-reader /path/to/paper.pdf
```

输出：
```
paper_digest_<作者>_<年份>_<标题>/
├── digest.html                  # 交互式可视化摘要
├── evidence_ledger.json         # 论断级源文映射
├── guard_report.md              # 反幻觉报告（人类可读）
└── guard_report.json            # 反幻觉报告（机器可读）
```

### 详细程度

| 级别 | 字数要求 | 解读范围 | 证明 |
|------|---------|---------|------|
| standard | 原文 1/2 | 仅主要结果 | 概述 |
| **premium**（默认） | 原文 2/3 | 所有结果 | 策略 + 关键步骤 |
| deep | 完整复现 | 所有条目 | 完整复现 |

### 模板说明

| 模板 | 适用场景 |
|------|---------|
| `premium_academic` | 通用论文，默认选择 |
| `theory` | 含引理、定理、证明的理论论文 |
| `empirical` | 回归分析为主的实证论文 |
| `review` | 综述文章（Annual Reviews、JEL、Handbook 章节） |
| `comparative` | 两篇论文的并排对比 |

### 工作流程

```
输入 -> 文本提取 -> AI 全文分析 -> 构建证据账本 -> 生成 HTML -> 运行守卫验证
```

AI 代理读取完整论文，提取所有形式化结果，构建论断级证据账本，生成 HTML 摘要，然后通过反幻觉守卫验证全部内容。若守卫返回 FAIL，代理迭代修正直至 PASS。

### Premium Academic 模板布局

默认模板为宽屏优化的三栏布局：

- **左侧边栏**（280px）：粘性目录，活跃章节追踪
- **主内容区**（弹性，最大 860px）：章节、论断卡片、公式块、解读框
- **右侧面板**（260px）：论文速览、证据质量仪表、关键贡献、符号速查、动态章节指示

右侧面板在 1200px 以下自动隐藏。768px 以下切换为单栏移动端布局。

---

<a name="español"></a>

## Descripcion

Paper Visual Reader convierte articulos academicos en PDF/LaTeX en resumenes HTML interactivos e independientes que son **mas informativos que leer el articulo original**. Cada afirmacion se rastrea hasta su fuente, cada ecuacion se renderiza con KaTeX y un guardian anti-alucinacion asegura que nada sea fabricado.

### Caracteristicas

- **Plantilla Premium Academic**: Diseno de tres paneles (indice lateral + contenido principal + panel de margen derecho) con tipografia serif Crimson Pro, alternancia de tema claro/oscuro y barra de progreso de lectura
- **5 plantillas especializadas**: Premium Academic (por defecto), Theory, Empirical, Review/Survey, Comparative
- **Control de evidencia**: Cada afirmacion tiene un nivel de severidad (Strong / Moderate / Weak) con anclas a la fuente
- **Guardian anti-alucinacion**: Validador deterministico que bloquea afirmaciones sin fundamento antes de la entrega
- **Renderizado matematico KaTeX**: Soporte completo de formulas LaTeX con proteccion automatica de desbordamiento
- **Interfaz interactiva**: Busqueda/filtrado de secciones, glosario de notacion modal, indice con desplazamiento suave y seguimiento activo
- **Panel de margen derecho**: Estadisticas rapidas, medidor de calidad de evidencia, referencia rapida de notacion clave, indicador dinamico de seccion

### Inicio rapido

```
paper-visual-reader /ruta/al/articulo.pdf
```

Salida:
```
paper_digest_<Autor>_<Ano>_<Titulo>/
├── digest.html                  # Resumen visual interactivo
├── evidence_ledger.json         # Mapeo de afirmaciones a fuentes
├── guard_report.md              # Informe anti-alucinacion (legible)
└── guard_report.json            # Informe anti-alucinacion (maquina)
```

### Niveles de detalle

| Nivel | Palabras | Interpretacion | Demostraciones |
|-------|----------|----------------|----------------|
| standard | 1/2 de la fuente | Solo resultados principales | Esquema |
| **premium** (por defecto) | 2/3 de la fuente | Todos los resultados | Estrategia + pasos clave |
| deep | Reproduccion completa | Todos los elementos | Reproduccion completa |

### Plantillas

| Plantilla | Uso ideal |
|-----------|----------|
| `premium_academic` | Articulos generales, opcion por defecto |
| `theory` | Articulos con lemas, teoremas, demostraciones |
| `empirical` | Trabajo empirico con regresiones |
| `review` | Articulos de revision (Annual Reviews, JEL, Handbooks) |
| `comparative` | Comparacion lado a lado de dos articulos |

### Arquitectura

```
ENTRADA -> EXTRAER_TEXTO -> ANALISIS IA -> CONSTRUIR_LIBRO_EVIDENCIA -> GENERAR_HTML -> EJECUTAR_GUARDIAN
```

El agente IA lee el articulo completo, extrae todos los resultados formales, construye un libro de evidencia a nivel de afirmacion, genera el resumen HTML y luego valida todo a traves del guardian anti-alucinacion. Si el guardian devuelve FAIL, el agente itera hasta obtener PASS.

### Diseno de la plantilla Premium Academic

La plantilla por defecto presenta un diseno de tres columnas optimizado para pantallas anchas:

- **Barra lateral izquierda** (280px): Indice fijo con seguimiento de seccion activa
- **Contenido principal** (flexible, max 860px): Secciones, tarjetas de afirmaciones, bloques de ecuaciones, cajas de interpretacion
- **Panel derecho** (260px): Estadisticas del articulo, medidor de calidad de evidencia, contribuciones clave, referencia rapida de notacion, indicador dinamico de seccion

El panel derecho se oculta por debajo de 1200px. Por debajo de 768px, el diseno cambia a una sola columna para moviles.

---

<div align="center">

Built for researchers who want to understand papers deeply, not just skim them.

</div>
