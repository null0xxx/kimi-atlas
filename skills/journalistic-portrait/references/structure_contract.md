# Structure Contract - Southern People Weekly Page Layouts

Extracted from 4-page PDF analysis of Southern People Weekly (南方人物周刊).

## Document Section Hierarchy

The magazine consists of three distinct page types, each with a rigid structure:

1. **Cover Page** (封面) - Page 1
2. **Table of Contents Page** (目录) - Page 2 (single page)
3. **Article Inner Pages** (内页文章) - Pages 3+

---

## Page Type 1: Cover Page

### CRITICAL: The cover uses a 3-layer z-index stack (see Rule 1 in SKILL.md)

### Complete Cover Structure

```
┌─────────────────────────────────────────────────────────────┐  ← Layer 2: Red border (12px #D90712)
│ ┌─────────────────────────────────────────────────────────┐ │     + inner white gap + inner line
│ │                                                         │ │
│ │   时 代 的 肖 像  (slogan, centered top)                 │ │
│ │                                                         │ │
│ │   ┌───┐  人 物 周 刊  (masthead, large bold italic)      │ │  ← Layer 1
│ │   │南 │                                                │ │     Masthead + headlines
│ │   │方 │                                                │ │
│ │   └───┘                                                │ │
│ │                                                         │ │
│ │   ┌──────────────────────────────────────────────┐     │ │
│ │   │                                              │     │ │
│ │   │      COVER PHOTO (full-bleed)                │     │ │  ← Layer 0
│ │   │                                              │     │ │     Background photo
│ │   │   刘震云 (headline name)                     │     │ │
│ │   │   写出无名的大人物 (subtitle)                 │     │ │
│ │   │   ─── (red accent bar)                       │     │ │
│ │   │   本刊记者 蒯乐昊 (author)                    │     │ │
│ │   │                                              │     │ │
│ │   │                        P62 文化               │     │ │  ← Layer 2
│ │   │                        一个普通读者...         │     │ │     TOC teasers
│ │   │                        ───                    │     │ │     (right side)
│ │   │                        P70 娱乐               │     │ │
│ │   │                        《镖人》...             │     │ │
│ │   │                        ───                    │     │ │
│ │   │                        + P38 国际             │     │ │
│ │   │                        伊朗的禁军...          │     │ │
│ │   │                                              │     │ │
│ │   │ [ISSN][条码][QR] 定价:15元 总第865期... www  │     │ │  ← Bottom info bar
│ │   └──────────────────────────────────────────────┘     │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### DOM Structure

```html
<div class="cover-container">
  <!-- Layer 0: Background Photo -->
  <div class="cover-bg">
    <img src="cover-photo.jpg" alt="Cover" class="cover-photo">
    <div class="cover-bg-overlay"></div>
  </div>

  <!-- Layer 1: Masthead + Headlines -->
  <div class="cover-masthead">
    <!-- Slogan at very top -->
    <div class="cover-slogan">时 代 的 肖 像</div>

    <!-- Logo area: "南方" + "人物周刊" -->
    <div class="cover-logo">
      <span class="logo-nanfang">南方</span>
      <span class="logo-title">人物周刊</span>
    </div>

    <!-- Cover headline (lower-left) -->
    <div class="cover-headline">
      <h1 class="cover-name">封面人物姓名</h1>
      <h2 class="cover-subtitle">封面副标题描述</h2>
      <div class="accent-bar"></div>
      <p class="cover-author">本刊记者 记者姓名</p>
    </div>
  </div>

  <!-- Layer 2: Frame + Teasers + Bottom Bar -->
  <div class="cover-frame"></div>

  <!-- Right-side teaser boxes -->
  <div class="cover-teasers">
    <div class="teaser">
      <div class="teaser-accent"></div>
      <div class="teaser-meta">
        <span class="teaser-page">P62</span>
        <span class="teaser-section">文化</span>
      </div>
      <p class="teaser-title">文章标题描述</p>
    </div>
    <div class="teaser">
      <div class="teaser-accent"></div>
      <div class="teaser-meta">
        <span class="teaser-page">P70</span>
        <span class="teaser-section">娱乐</span>
      </div>
      <p class="teaser-title">文章标题描述</p>
    </div>
    <div class="teaser teaser-highlight">
      <div class="teaser-accent"></div>
      <div class="teaser-meta">
        <span class="teaser-plus">+</span>
        <span class="teaser-page">P38</span>
        <span class="teaser-section">国际</span>
      </div>
      <p class="teaser-title">国际文章标题</p>
    </div>
  </div>

  <!-- Bottom info bar -->
  <div class="cover-bottom-bar">
    <div class="bar-left">
      <span class="bar-issn">ISSN 1672-8335</span>
      <span class="bar-barcode">[BARCODE]</span>
      <span class="bar-qr">[QR]</span>
    </div>
    <div class="bar-center">
      <span>定价：人民币15元 港币30元</span>
      <span>总第865期 2026年3月16日 第7期</span>
      <span>国内统一刊号 CN44-1614/C</span>
    </div>
    <div class="bar-right">
      <span>www.nfpeople.com</span>
    </div>
  </div>
</div>
```

### Cover CSS Key Rules

- `.cover-container { position: relative; width: 100%; aspect-ratio: 3/4; min-height: 900px; overflow: hidden; }`
- `.cover-bg { position: absolute; z-index: 0; inset: 20px; }`
- `.cover-bg img { width: 100%; height: 100%; object-fit: cover; filter: saturate(0.85); }`
- `.cover-bg-overlay { position: absolute; inset: 0; background: linear-gradient(to bottom, rgba(0,0,0,0.1), rgba(0,0,0,0.45)); }`
- `.cover-masthead { position: absolute; z-index: 1; inset: 20px; display: flex; flex-direction: column; }`
- `.cover-frame { position: absolute; z-index: 2; inset: 0; border: 12px solid #D90712; pointer-events: none; }`
- `.cover-frame::after { content: ''; position: absolute; inset: 8px; border: 2px solid rgba(255,255,255,0.6); }`
- `.cover-teasers { position: absolute; z-index: 2; right: 60px; bottom: 120px; color: #fff; text-align: right; }`
- `.cover-bottom-bar { position: absolute; z-index: 2; bottom: 20px; left: 20px; right: 20px; display: flex; justify-content: space-between; align-items: center; padding: 10px 20px; background: rgba(0,0,0,0.3); color: #fff; font-size: 11px; }`
- `.teaser-accent { width: 20px; height: 2px; background: #D90712; margin-bottom: 6px; }`
- `.teaser-highlight .teaser-plus { display: inline-flex; width: 20px; height: 20px; border-radius: 50%; background: #fff; color: #D90712; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; margin-right: 4px; }`

### Cover CRITICAL Requirements

1. **Masthead must read "南方" + "人物周刊"** - not "南方人物周刊" as one line
2. **Teaser boxes MUST be present** on right side with P[number] section title format
3. **Bottom info bar MUST include**: ISSN, barcode, QR code, price, issue info, website
4. **Red border frame** with inner white line gap
5. **"国际" teaser** has special "+" icon in white circle

---

## Page Type 2: Table of Contents Page

### CRITICAL: TOC MUST fit on a SINGLE page

### Structure

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  │ CONTENTS                                                  │
│  │ 目录              (left black bar + bilingual header)    │
│                                                             │
│                                                             │
│              ┌──────────────────────┐                       │
│              │                      │                       │
│              │   PORTRAIT PHOTO     │                       │
│              │   (centered, ~45%)   │                       │
│              │                      │                       │
│              └──────────────────────┘                       │
│                       图/本刊记者 姜晓明                     │
│                                                             │
│                       14                                    │
│              COVER STORY 封面人物                            │
│                                                             │
│                    刘震云                                    │
│           毫不幽默的"幽默大师"                              │
│          写出一群名不见经传的大人物                          │
│                                                             │
│                                                             │
│  ───────────────────────────────────────────────────────    │
│  06 VIEWPOINTS  │  78 SUPPLEMENT  │  80 COLUMNS             │
│     世界观      │     后窗        │    专栏                  │
│  ───────────────────────────────────────────────────────    │
│                                                             │
│  2                                                          │
└─────────────────────────────────────────────────────────────┘
```

### DOM Structure

```html
<div class="toc-page">
  <header class="toc-header">
    <div class="toc-bar"></div>
    <div class="toc-titles">
      <h1 class="toc-en">CONTENTS</h1>
      <h2 class="toc-cn">目录</h2>
    </div>
  </header>

  <main class="toc-main">
    <figure class="toc-photo">
      <img src="portrait.jpg" alt="Cover figure">
      <figcaption>图/本刊记者 摄影师名</figcaption>
    </figure>

    <div class="toc-featured">
      <div class="toc-page-number">14</div>
      <div class="toc-label">
        <span class="label-en">COVER STORY</span>
        <span class="label-cn">封面人物</span>
      </div>
      <h3 class="toc-person">刘震云</h3>
      <p class="toc-description">毫不幽默的"幽默大师"</p>
      <p class="toc-description">写出一群名不见经传的大人物</p>
    </div>
  </main>

  <nav class="toc-nav">
    <div class="nav-item">
      <span class="nav-number">06</span>
      <div class="nav-labels">
        <span class="nav-en">VIEWPOINTS</span>
        <span class="nav-cn">世界观</span>
      </div>
    </div>
    <div class="nav-divider"></div>
    <div class="nav-item">
      <span class="nav-number">78</span>
      <div class="nav-labels">
        <span class="nav-en">SUPPLEMENT</span>
        <span class="nav-cn">后窗</span>
      </div>
    </div>
    <div class="nav-divider"></div>
    <div class="nav-item">
      <span class="nav-number">80</span>
      <div class="nav-labels">
        <span class="nav-en">COLUMNS</span>
        <span class="nav-cn">专栏</span>
      </div>
    </div>
  </nav>

  <div class="page-number">2</div>
</div>
```

### TOC CSS Key Rules

- `.toc-page { max-width: 1200px; margin: 0 auto; padding: 60px 40px 40px; background: #fff; min-height: 100vh; display: flex; flex-direction: column; justify-content: space-between; }`
- `.toc-header { display: flex; align-items: flex-start; margin-bottom: 30px; }`
- `.toc-bar { width: 4px; height: 60px; background: #000; margin-right: 15px; flex-shrink: 0; }`
- `.toc-en { font-size: 42px; font-weight: 400; letter-spacing: 0.05em; color: #000; }`
- `.toc-cn { font-size: 24px; font-weight: 700; color: #000; }`
- `.toc-photo { text-align: center; margin: 30px 0; }`
- `.toc-photo img { max-width: 45%; aspect-ratio: 3/4; object-fit: cover; }`
- `.toc-photo figcaption { font-size: 12px; color: #666; text-align: right; padding-right: 27.5%; }`
- `.toc-page-number { font-size: 48px; font-weight: 300; text-align: center; color: #000; }`
- `.toc-label { text-align: center; font-size: 13px; margin: 10px 0; }`
- `.toc-person { font-size: 36px; font-weight: 700; text-align: center; margin: 15px 0; }`
- `.toc-description { font-size: 24px; text-align: center; color: #000; margin: 5px 0; }`
- `.toc-nav { display: flex; justify-content: space-around; align-items: center; border-top: 1px solid #1A1A1A; border-bottom: 1px solid #1A1A1A; padding: 20px 0; margin-top: auto; }`
- `.nav-divider { width: 1px; height: 40px; background: #1A1A1A; }`
- `.nav-item { text-align: center; }`
- `.nav-number { font-size: 36px; font-weight: 300; display: block; }`

### TOC CRITICAL Requirements

1. **MUST fit on ONE page** - use `margin-top: auto` to push nav to bottom
2. **Black vertical bar** (4px x 60px) to the left of CONTENTS/目录
3. **Photo centered** at ~45% width, portrait aspect ratio
4. **Nav bar at bottom** with 3 columns separated by vertical dividers
5. **Page number "2"** at bottom-left

---

## Page Type 3: Article Inner Page

### CRITICAL: Articles use TWO-COLUMN layout from the FIRST page

### Structure

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                    VIEWPOINTS                               │
│                    世界观                                   │
│                      👁                                     │
│  ───────────────────────────────────────────────────────    │
│                                                             │
│              REPORTER'S VIEW 记者眼                         │
│                                                             │
│           想了解作家？那就去读书吧！                         │
│                                                             │
│    本刊记者 蒯乐昊 编辑 李屾淼 lishenmiao1989@126.com        │
│                                                             │
│  ┌──────────────────┐  ┌─────────────────────────────────┐ │
│  │                  │  │  好醋包一顿饺子，为一摞筋道的    │ │
│  │                  │  │  饺子皮绞拌出巨大的馅...         │ │
│  │    PHOTO         │  │                                 │ │
│  │    (floated      │  │  比起采访时作家说了什么，        │ │
│  │     right)       │  │  我似乎更相信他写了什么...       │ │
│  │                  │  │                                 │ │
│  │  刘震云           │  │  所以，你可以不读这篇报道，      │ │
│  │  图/本刊记者      │  │  直接去读书吧！▼                │ │
│  │  姜晓明           │  │                                 │ │
│  └──────────────────┘  └─────────────────────────────────┘ │
│                                                             │
│  ───────────────────────────────────────────────────────    │
│  详看本期封面报道                                            │
│  《刘震云 毫不幽默的"幽默大师"》                            │
│                                                             │
│  6                                                          │
└─────────────────────────────────────────────────────────────┘
```

### DOM Structure

```html
<div class="article-page">
  <header class="section-header">
    <div class="section-en">VIEWPOINTS</div>
    <div class="section-cn">世界观</div>
    <div class="section-icon">
      <!-- SVG eye icon -->
      <svg viewBox="0 0 24 24" width="20" height="20"><circle cx="12" cy="12" r="4"/><path d="M2 12s4-8 10-8 10 8 10 8-4 8-10 8S2 12 2 12z"/></svg>
    </div>
    <div class="section-divider"></div>
    <div class="subsection">
      <span class="subsection-en">REPORTER'S VIEW</span>
      <span class="subsection-cn">记者眼</span>
    </div>
  </header>

  <article class="article-content">
    <h1 class="article-title">想了解作家？那就去读书吧！</h1>
    <p class="article-author">
      <span>本刊记者 蒯乐昊</span>
      <span>编辑 李屾淼</span>
      <span>lishenmiao1989@126.com</span>
    </p>

    <!-- DUAL-COLUMN from the first page -->
    <div class="article-body dual-column">
      <!-- First column -->
      <div class="column">
        <p class="has-indent">刘震云常写延津，大家因此熟悉了这座中原小城...</p>
        <p class="has-indent">他笔下的延津城...</p>
        <!-- More paragraphs to fill 800-1000 chars per page -->
      </div>

      <!-- Second column -->
      <div class="column">
        <figure class="article-image right">
          <img src="photo.jpg" alt="Description">
          <figcaption>人物名 图/本刊记者 摄影师</figcaption>
        </figure>
        <p class="has-indent">好醋包一顿饺子...</p>
        <p class="has-indent">比起采访时作家说了什么...<span class="end-triangle">▼</span></p>
      </div>
    </div>

    <div class="article-footer">
      <div class="footer-divider"></div>
      <p class="footer-note">详看本期封面报道</p>
      <p class="footer-title">《刘震云 毫不幽默的"幽默大师"》写出一群名不见经传的大人物》</p>
    </div>
  </article>

  <div class="page-number">6</div>
</div>
```

### Article CSS Key Rules

- `.article-page { max-width: 1200px; margin: 0 auto; padding: 40px; background: #fff; }`
- `.section-header { text-align: center; margin-bottom: 20px; }`
- `.section-en { font-size: 18px; letter-spacing: 0.05em; text-transform: uppercase; color: #000; }`
- `.section-cn { font-size: 16px; font-weight: 700; color: #000; }`
- `.section-icon { margin: 8px 0; display: flex; justify-content: center; }`
- `.section-icon svg { stroke: #1A1A1A; fill: none; stroke-width: 1.5; }`
- `.section-divider { border-top: 1px solid #1A1A1A; margin: 10px 0; }`
- `.subsection { font-size: 12px; margin: 15px 0; }`
- `.subsection-en { letter-spacing: 0.05em; text-transform: uppercase; margin-right: 8px; }`
- `.article-title { font-size: 32px; font-weight: 700; text-align: center; margin: 30px 0 15px; color: #1A1A1A; line-height: 1.3; }`
- `.article-author { text-align: center; color: #666; font-size: 13px; margin-bottom: 40px; }`
- `.dual-column { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }`
- `.has-indent { text-indent: 2em; }`
- `.article-image { float: right; margin: 0 0 1em 1.5em; max-width: 48%; }`
- `.article-image img { width: 100%; display: block; }`
- `.article-image figcaption { font-size: 12px; color: #666; text-align: right; margin-top: 0.5em; }`
- `.end-triangle { color: #D90712; font-size: 8px; margin-left: 0.3em; }`
- `.article-footer { margin-top: 40px; }`
- `.footer-divider { border-top: 1px solid #1A1A1A; margin: 20px 0 15px; }`
- `.footer-note { font-size: 13px; color: #666; margin-bottom: 5px; }`
- `.footer-title { font-size: 13px; color: #666; }`
- `.page-number { font-size: 12px; color: #999; margin-top: 40px; }`

### Article CRITICAL Requirements

1. **TWO-COLUMN layout from the FIRST page** - never single column
2. **800-1000 characters per page** - generate enough text to fill the page
3. **First paragraph after title has NO indent** - remove `text-indent` for first paragraph
4. **Images use `float`** - never `position: absolute` (Rule 2)
5. **Parent of floated images MUST have clearfix** - use `::after { content: ""; display: table; clear: both; }`
6. **Red triangle ▼ at end of final paragraph** - inline, no space before
7. **Footer section** with divider + "详看本期封面报道" + cover story title
8. **Page numbers** at bottom, consistent placement

### Article with No Images (text-only)

When an article page has no images, both columns contain only text:

```
┌─────────────────────────────────────────────────────────────┐
│  VIEWPOINTS / 世界观 + eye icon + divider                   │
│  MILITARY 军事                                               │
│  美国为打击伊朗准备了二十多年                                │
│  文 朱江明 编辑 李屾淼 ...                                   │
│                                                             │
│  ┌────────────────────────┐  ┌────────────────────────────┐ │
│  │ 美国和以色列对伊朗的   │  │ 将熟悉美国军队的战术和弱点，│ │
│  │ 战事已经进行了十多天... │  │ 开战第一天...                │ │
│  │                        │  │                              │ │
│  │ 伊朗的反击相当激烈...  │  │ 2000年10月12日...            │ │
│  │                        │  │                              │ │
│  │ 2002年夏天...          │  │ 里佩尔的做法并非天马行空...   │ │
│  │                        │  │                              │ │
│  │ ...                    │  │ ...                         │ │
│  │                        │  │ ...▼                        │ │
│  └────────────────────────┘  └────────────────────────────┘ │
│  详看本期封面报道...                                         │
│  7                                                          │
└─────────────────────────────────────────────────────────────┘
```

For text-only pages, distribute paragraphs evenly across both columns.

---

## Cross-Page Navigation

- Cover page links to TOC page
- TOC page links to all section start pages via bottom nav
- Article pages have "详看本期封面报道" footer linking back to cover story
- Page numbers increment sequentially (Cover=1, TOC=2, articles continue)

## Responsive Behavior

On screens narrower than 768px:
- Dual-column becomes single-column
- Cover teasers move below headline area
- TOC nav stacks vertically
- Font sizes reduce by 15-20%
- Cover border reduces to 6px
