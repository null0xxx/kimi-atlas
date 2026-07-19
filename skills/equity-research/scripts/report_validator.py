#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研报结构自动化预检脚本
Automated Structural Pre-check for Investment Research Reports

检查内容：不判断内容质量，只验证"必填结构元素是否存在"

用法:
    python report_validator.py --html /path/to/report.html --json
    python report_validator.py --html /path/to/report.html  # 人类可读输出
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Any
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("错误：需要安装 beautifulsoup4。请运行: pip install beautifulsoup4")
    sys.exit(1)


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    details: List[str] = field(default_factory=list)


class ReportValidator:
    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, "html.parser")
        self.results: List[CheckResult] = []

    def run_all(self, mode: str = "auto") -> List[CheckResult]:
        """Run all checks. mode: 'tear_sheet', 'equity_report', or 'auto' (detect from HTML)."""
        if mode == "auto":
            mode = self.detect_mode()

        # --- Shared checks (both modes) ---
        self.check_exhibit_continuity()
        self.check_data_source_presence()
        self.check_key_assumptions_table()
        self.check_bull_bear_debate()
        self.check_earnings_quality_signal()
        self.check_catalyst_count()
        self.check_module_titles()
        self.check_capital_flow_mention()
        self.check_change_highlight()
        self.check_industry_chain_diagram()
        self.check_stock_chart()
        self.check_supply_chain_svg()
        self.check_container_class()
        self.check_page_balance(mode)

        # --- Equity report specific checks ---
        if mode == "equity_report":
            self.check_dcf_section()
            self.check_sensitivity_matrix()
            self.check_historical_band()
            self.check_cross_method_synthesis()
            self.check_chart_exhibits()

        return self.results

    def detect_mode(self) -> str:
        """Auto-detect whether this is a tear sheet or equity report."""
        text = self.soup.get_text()
        # Equity report indicators: DCF, sensitivity matrix, cover-split layout
        equity_signals = [
            self.soup.find(class_="cover-split") is not None,
            "DCF" in text or "折现现金流" in text,
            "sensitivity" in text.lower() or "敏感性" in text,
            self.soup.find(class_="sensitivity-matrix") is not None,
        ]
        return "equity_report" if sum(equity_signals) >= 2 else "tear_sheet"

    def check_exhibit_continuity(self):
        """检查 Exhibit 编号是否连续"""
        text = self.soup.get_text()
        # 匹配 "图表 1:" 或 "Exhibit 1:"
        pattern = re.compile(r'(?:图表|Exhibit)\s+(\d+):', re.IGNORECASE)
        numbers = [int(m.group(1)) for m in pattern.finditer(text)]

        if not numbers:
            self.results.append(CheckResult(
                "exhibit_continuity", False,
                "未找到任何 Exhibit 编号",
                ["报告中应包含 '图表 X:' 或 'Exhibit X:' 编号"]
            ))
            return

        expected = list(range(min(numbers), max(numbers) + 1))
        missing = [n for n in expected if n not in numbers]
        duplicates = [n for n in set(numbers) if numbers.count(n) > 1]

        details = []
        if missing:
            details.append(f"缺失编号: {missing}")
        if duplicates:
            details.append(f"重复编号: {duplicates}")

        passed = not missing and not duplicates
        self.results.append(CheckResult(
            "exhibit_continuity", passed,
            f"找到 {len(numbers)} 个 Exhibit 编号，范围 {min(numbers)}-{max(numbers)}" + (
                "" if passed else "，但存在缺失或重复"
            ),
            details
        ))

    def check_data_source_presence(self):
        """检查每个表格/图表下方是否有数据来源标注"""
        tables = self.soup.find_all("table")
        charts = self.soup.find_all("div", class_="chart-container")
        mermaids = self.soup.find_all("div", class_="mermaid-container")

        missing_sources = []
        for table in tables:
            # 查找紧随其后的 .data-source（在同一父元素内或相邻）
            parent = table.find_parent()
            next_sibling = table.find_next_sibling()
            has_source = False
            if next_sibling and "data-source" in (next_sibling.get("class") or []):
                has_source = True
            else:
                # 在父元素内查找
                sources = parent.find_all("div", class_="data-source") if parent else []
                has_source = len(sources) > 0
            if not has_source:
                # 尝试获取表格标题上下文
                caption = ""
                prev = table.find_previous(["div"], class_="exhibit-label")
                if prev:
                    caption = prev.get_text(strip=True)[:40]
                missing_sources.append(f"表格 {caption}")

        for chart in charts:
            parent = chart.find_parent()
            next_sibling = chart.find_next_sibling()
            has_source = False
            if next_sibling and "data-source" in (next_sibling.get("class") or []):
                has_source = True
            else:
                sources = parent.find_all("div", class_="data-source") if parent else []
                has_source = len(sources) > 0
            if not has_source:
                missing_sources.append("股价图")

        for mermaid in mermaids:
            parent = mermaid.find_parent()
            next_sibling = mermaid.find_next_sibling()
            has_source = False
            if next_sibling and "data-source" in (next_sibling.get("class") or []):
                has_source = True
            else:
                sources = parent.find_all("div", class_="data-source") if parent else []
                has_source = len(sources) > 0
            if not has_source:
                missing_sources.append("产业链图")

        passed = len(missing_sources) == 0
        self.results.append(CheckResult(
            "data_source_presence", passed,
            f"检查了 {len(tables)} 个表格、{len(charts)} 个图表、{len(mermaids)} 个Mermaid图" + (
                "，全部有数据来源标注" if passed else f"，{len(missing_sources)} 处缺失: {', '.join(missing_sources[:3])}"
            ),
            missing_sources
        ))

    def check_key_assumptions_table(self):
        """检查投资逻辑模块是否包含关键假设（独立表或合并的投资论点综合分析表均可），≥4行数据"""
        tables = self.soup.find_all("table")
        target_table = None
        for table in tables:
            text = table.get_text()
            # 合并表识别：同时包含假设关键词 AND 多空关键词
            has_assumption = "关键假设" in text or "拐点信号" in text or \
                            "Key Assumption" in text or "Inflection Signal" in text or "Inflection" in text
            has_bull_bear = "多头" in text or "空头" in text or "Bull" in text or "Bear" in text
            # 独立表或合并表都接受
            if has_assumption:
                target_table = table
                break

        if not target_table:
            self.results.append(CheckResult(
                "key_assumptions_table", False,
                "未找到关键假设验证表或投资论点综合分析表",
                ["投资逻辑模块中应包含含'关键假设'的表格（独立或合并均可）"]
            ))
            return

        rows = target_table.find_all("tr")
        data_rows = [r for r in rows if r.find("td")]
        passed = len(data_rows) >= 4
        self.results.append(CheckResult(
            "key_assumptions_table", passed,
            f"找到假设验证表，共 {len(data_rows)} 行数据" + (
                "（≥4行，符合要求）" if passed else "（<4行，需要至少4个维度行）"
            ),
            []
        ))

    def check_bull_bear_debate(self):
        """检查投资逻辑模块是否包含多空 debate 表格（独立或合并的投资论点综合分析表均可）"""
        tables = self.soup.find_all("table")
        target_table = None
        for table in tables:
            text = table.get_text()
            if ("多头" in text and "空头" in text) or ("Bull" in text and "Bear" in text) or "多空" in text:
                headers = [th.get_text(strip=True) for th in table.find_all("th")]
                if any("多头" in h or "Bull" in h or "论据" in h or "观点" in h for h in headers):
                    target_table = table
                    break

        passed = target_table is not None
        self.results.append(CheckResult(
            "bull_bear_debate", passed,
            "找到多空Debate表格（独立或合并均可）" if passed else "未找到多空Debate表格",
            [] if passed else ["投资逻辑模块中应包含含'多头'/'空头'论据的表格"]
        ))

    def check_earnings_quality_signal(self):
        """检查财务分析模块是否包含'盈利质量信号'文本"""
        text = self.soup.get_text()
        text_lower = text.lower()
        passed = (
            "盈利质量" in text or "盈利现金含量" in text or "OCF/净利润" in text
            or "earnings quality" in text_lower or "ocf/net income" in text_lower
            or ("operating cash flow" in text_lower and "net income" in text_lower)
        )
        self.results.append(CheckResult(
            "earnings_quality_signal", passed,
            "财务分析模块包含盈利质量信号" if passed else "未在报告中找到'盈利质量'相关文本",
            [] if passed else ["财务分析模块中应包含'盈利质量信号'段落，提及OCF/NI、非经常性损益等指标"]
        ))

    def check_catalyst_count(self):
        """检查催化剂日历是否包含 ≥4 个事件"""
        # 查找包含"催化剂"或"Catalyst"文本的表格
        tables = self.soup.find_all("table")
        target_table = None
        for table in tables:
            caption = table.find_previous(["div"], class_="exhibit-label")
            if caption and ("催化剂" in caption.get_text() or "Catalyst" in caption.get_text()):
                target_table = table
                break
            # 备用：通过表头判断
            headers = [th.get_text(strip=True) for th in table.find_all("th")]
            if any("催化剂" in h or "Catalyst" in h or "事件" in h for h in headers):
                target_table = table
                break

        if not target_table:
            self.results.append(CheckResult(
                "catalyst_count", False,
                "未找到催化剂日历表格",
                ["报告中应包含一个标题含'催化剂'或'Catalyst'的表格"]
            ))
            return

        rows = target_table.find_all("tr")
        data_rows = [r for r in rows if r.find("td")]
        passed = len(data_rows) >= 4
        self.results.append(CheckResult(
            "catalyst_count", passed,
            f"催化剂日历包含 {len(data_rows)} 个事件" + (
                "（≥4个，符合要求）" if passed else "（<4个，需要至少4个事件）"
            ),
            []
        ))

    def check_module_titles(self):
        """检查模块标题是否符合标准清单（支持中英文）"""
        text = self.soup.get_text()
        # 英文版判断：优先检查实际 HTML 元素是否有 report-container-en class（排除 <style> 标签）
        en_container = self.soup.find(attrs={"class": lambda x: x and "report-container-en" in x.split()})
        has_en_class = en_container is not None
        # 备用判断：如果有2个及以上的英文模块标题，视为英文版
        en_title_count = sum(1 for t in ["Company Overview", "Investment Thesis", "Valuation", "Industry Chain", "Financial Analysis"] if t in text)
        is_english = has_en_class or en_title_count >= 2

        if is_english:
            required_pairs = [
                ("Company Overview" in text, "公司概览"),
                ("Investment Thesis" in text or "Investment Logic" in text, "投资逻辑/Investment Thesis"),
                ("Valuation" in text, "估值分析/Valuation"),
                ("Industry" in text or "Comparable" in text, "行业/可比公司"),
                ("Supply Chain" in text or "Industry Chain" in text, "产业链"),
                ("Financial Analysis" in text, "财务分析"),
                ("Risk" in text or "Scenario" in text, "情景/风险"),
            ]
            missing = [label for condition, label in required_pairs if not condition]
        else:
            required_titles = [
                "公司概览",
                "投资逻辑",
                "估值分析与催化剂",
                "行业与估值对比",
                "产业链全景",
                "上下游深度分析",
                "财务分析",
                "情景分析与风险提示",
            ]
            missing = [t for t in required_titles if t not in text]

        passed = len(missing) == 0
        self.results.append(CheckResult(
            "module_title_compliance", passed,
            "所有标准模块标题均已找到" if passed else f"缺失模块标题: {missing}",
            missing if missing else []
        ))

    def check_capital_flow_mention(self):
        """检查短期投资逻辑是否包含资金面/盘面结构分析"""
        text = self.soup.get_text()
        keywords = [
            "解禁", "增减持", "减持", "增持", "定向增发", "定增", "回购",
            "北向资金", "主力资金", "资金面", "盘面", "大股东",
            "lock-up", "unlock", "shareholder reduction", "buyback",
            "northbound", "capital flow", "major shareholder"
        ]
        matches = [kw for kw in keywords if kw in text]
        passed = len(matches) >= 1
        self.results.append(CheckResult(
            "capital_flow_mention", passed,
            f"短期投资逻辑/报告中提及资金面关键词: {matches[:3]}" if passed else "未在报告中找到解禁、增减持、定增、回购、北向资金、主力资金等资金面/盘面结构关键词",
            [] if passed else ["短期投资逻辑必须包含至少1项资金面/盘面结构分析（如解禁、增减持、回购、资金流向）"]
        ))

    def check_industry_chain_diagram(self):
        """检查产业链模块使用了图表（HTML flex / Mermaid / 预渲染PNG），而非纯表格"""
        chain_wrappers = self.soup.select('.chain-wrapper')
        mermaid_containers = self.soup.select('.mermaid-container')
        mermaid_svgs = self.soup.select('.mermaid-container .mermaid')

        has_html_chain = any(
            node.select('.chain-box') for node in chain_wrappers
        )
        # Mermaid may be pre-rendered to PNG (embedded as <img>) — this is explicitly allowed
        has_mermaid_rendered = any(
            node.get_text(strip=True) for node in mermaid_svgs
        ) or any(
            node.select('img') for node in mermaid_containers
        )
        # Also accept: .mermaid-container with any content (pre-rendered PNG as <img>)
        has_mermaid_container = len(mermaid_containers) > 0

        passed = has_html_chain or has_mermaid_rendered or has_mermaid_container
        details = []
        if has_html_chain:
            details.append("HTML flex chain (.chain-wrapper) found")
        if has_mermaid_rendered:
            details.append("Mermaid diagram (SVG or pre-rendered PNG) found")
        elif has_mermaid_container:
            details.append("Mermaid container found (may be pre-rendered PNG)")

        self.results.append(CheckResult(
            "industry_chain_diagram", passed,
            "找到产业链图（" + ", ".join(details) + ")" if passed else
            "产业链模块未找到 .chain-wrapper 或 .mermaid-container — 禁止使用纯表格替代",
            [] if passed else [
                "产业链必须使用 HTML/CSS flex 布局（.chain-wrapper + .chain-box）或 Mermaid 图表（SVG或预渲染PNG）",
                "纯 <table> 表格或纯文字描述不符合要求",
                "Note: Mermaid pre-rendered to PNG via Playwright is valid — check .mermaid-container > img"
            ]
        ))

    def check_stock_chart(self):
        """检查52周股价图是否存在且base64长度足够（≥20,000字符表示有实际图像）"""
        imgs = self.soup.find_all("img")
        chart_img = None
        for img in imgs:
            src = img.get("src", "")
            alt = img.get("alt", "")
            if "base64" in src and ("stock" in alt.lower() or "股价" in alt or "price" in alt.lower()
                                     or len(src) > 20000):
                chart_img = img
                break

        if not chart_img:
            # Check for any large base64 image (likely stock chart)
            for img in imgs:
                src = img.get("src", "")
                if "base64" in src and len(src) > 20000:
                    chart_img = img
                    break

        if not chart_img:
            self.results.append(CheckResult(
                "stock_chart", False,
                "未找到股价图（base64 嵌入图像）",
                ["必须使用 scripts/stock_chart_generator.py 生成52周股价图并以 base64 嵌入"]
            ))
            return

        b64_len = len(chart_img.get("src", ""))
        passed = b64_len >= 20000
        self.results.append(CheckResult(
            "stock_chart", passed,
            f"找到股价图，base64长度: {b64_len:,}" + (
                "（≥20,000，正常）" if passed else "（<20,000，可能为占位符或损坏图像）"
            ),
            []
        ))

    def check_supply_chain_svg(self):
        """检查产业链使用了预渲染图像（SVG或PNG）或HTML flex，而非raw Mermaid代码"""
        text = self.soup.get_text()

        # Bad patterns: raw Mermaid code in HTML (these are real errors)
        has_raw_mermaid = bool(self.soup.find("pre", class_="mermaid"))

        # Detect mermaid script loading by inspecting <script> tags specifically,
        # not substring-matching the entire HTML. A substring check would
        # false-positive any time the report's prose mentions "mermaid.min.js" or
        # an email/handle containing "mermaid@" — neither indicates the page is
        # trying to execute mermaid JS.
        def _script_loads_mermaid(tag):
            src = (tag.get("src") or "").lower()
            if "mermaid" in src and (src.endswith(".js") or "mermaid@" in src):
                return True  # external mermaid script (including CDN versioned URLs)
            inline = (tag.string or "")
            return ("mermaid.initialize" in inline) or ("mermaid.init(" in inline)

        has_mermaid_script = any(
            _script_loads_mermaid(s) for s in self.soup.find_all("script")
        )

        # Good patterns: SVG, PNG (pre-rendered Mermaid), or HTML flex
        has_svg = bool(self.soup.find("svg"))
        has_svg_img = any(
            'image/svg+xml' in (img.get("src", "") or "")
            for img in self.soup.find_all("img")
        )
        # Mermaid → PNG pre-rendering is explicitly allowed by the skill
        has_png_img = any(
            'data:image/png;base64' in (img.get("src", "") or "")
            for img in self.soup.find_all("img")
            if img.find_parent(class_="mermaid-container") or img.find_parent(class_="chart-container-free")
        )
        has_chain_wrapper = bool(self.soup.select('.chain-wrapper .chain-box'))

        issues = []
        if has_raw_mermaid:
            issues.append("发现 <pre class='mermaid'> — raw Mermaid代码在PDF中不会渲染")
        if has_mermaid_script:
            issues.append("发现 mermaid.min.js 脚本引用 — PDF渲染器不执行JavaScript")

        has_valid_chain = has_svg or has_svg_img or has_png_img or has_chain_wrapper
        passed = has_valid_chain and not has_raw_mermaid and not has_mermaid_script

        self.results.append(CheckResult(
            "supply_chain_svg", passed,
            "产业链使用预渲染图像或HTML/CSS flex" if passed else
            "产业链渲染问题" + ("：" + "; ".join(issues) if issues else "：未找到SVG、PNG或chain-wrapper"),
            [] if passed else issues + [
                "Note: Mermaid pre-rendered to PNG (via Playwright) is valid — skill explicitly allows this",
                "Expected structure: .mermaid-container > .chart-container-free > img[src='data:image/png;base64,...']"
            ]
        ))

    def check_container_class(self):
        """检查report-container是否存在，且语言class是否匹配内容"""
        container = self.soup.find(class_="report-container")
        if not container:
            self.results.append(CheckResult(
                "container_class", False,
                "未找到 .report-container 容器",
                ["HTML必须包含 <div class='report-container'> 作为根容器"]
            ))
            return

        classes = container.get("class", [])
        is_en = "report-container-en" in classes

        # Heuristic: check if content is primarily English or Chinese
        text = container.get_text()
        # Count Chinese characters
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        total_chars = len(text)
        chinese_ratio = chinese_chars / max(total_chars, 1)

        issues = []
        if is_en and chinese_ratio > 0.3:
            issues.append(f"容器标记为英文版 (.report-container-en) 但中文字符占比 {chinese_ratio:.0%}，可能语言设置错误")
        elif not is_en and chinese_ratio < 0.05:
            issues.append(f"容器标记为中文版 (.report-container) 但中文字符占比仅 {chinese_ratio:.0%}，可能缺少 .report-container-en")

        passed = len(issues) == 0
        lang = "English" if is_en else "Chinese"
        self.results.append(CheckResult(
            "container_class", passed,
            f"容器class正确 ({lang}版)" if passed else f"容器class可能与内容语言不匹配",
            issues
        ))

    # --- Equity Report Specific Checks ---

    def check_dcf_section(self):
        """[Equity Report] 检查DCF模型是否包含假设表+FCF投影+equity bridge"""
        text = self.soup.get_text()
        text_lower = text.lower()
        signals = {
            "WACC": "wacc" in text_lower,
            "FCF projection": "fcf" in text_lower or "free cash flow" in text_lower or "自由现金流" in text,
            "Terminal value": "terminal" in text_lower or "终值" in text or "永续" in text,
            "Equity bridge": ("equity value" in text_lower or "per share" in text_lower
                              or "每股价值" in text or "股权价值" in text),
        }
        missing = [k for k, v in signals.items() if not v]
        passed = len(missing) == 0
        self.results.append(CheckResult(
            "dcf_section", passed,
            "DCF模型包含所有必要组件" if passed else f"DCF模型缺少: {', '.join(missing)}",
            missing
        ))

    def check_sensitivity_matrix(self):
        """[Equity Report] 检查敏感性矩阵是否存在且有base-case高亮"""
        matrix = self.soup.find(class_="sensitivity-matrix")
        if not matrix:
            # Fallback: look for table with WACC in headers
            tables = self.soup.find_all("table")
            for t in tables:
                headers = t.get_text()
                if "WACC" in headers and ("growth" in headers.lower() or "增长" in headers):
                    matrix = t
                    break

        if not matrix:
            self.results.append(CheckResult(
                "sensitivity_matrix", False,
                "未找到敏感性矩阵 (.sensitivity-matrix 或含WACC的表格)",
                ["估值部分必须包含 WACC × Terminal Growth 敏感性矩阵"]
            ))
            return

        has_base = matrix.find(class_="base-case") is not None
        issues = []
        if not has_base:
            issues.append("敏感性矩阵缺少 .base-case 高亮标记 — 基础假设单元格应加粗或标注")

        passed = has_base
        self.results.append(CheckResult(
            "sensitivity_matrix", passed,
            "敏感性矩阵存在" + ("且基础假设已高亮" if passed else "但基础假设未高亮"),
            issues
        ))

    def check_historical_band(self):
        """[Equity Report] 检查历史估值带是否包含PE/PB和百分位"""
        text = self.soup.get_text()
        has_band = ("percentile" in text.lower() or "百分位" in text or "分位" in text
                    or "+1σ" in text or "+1SD" in text or "标准差" in text)
        has_pe_pb = ("PE" in text and "PB" in text)

        passed = has_band and has_pe_pb
        issues = []
        if not has_band:
            issues.append("未找到百分位/标准差分析 — 历史估值带需包含当前百分位位置")
        if not has_pe_pb:
            issues.append("未同时找到PE和PB — 历史估值带至少需要2个指标")

        self.results.append(CheckResult(
            "historical_band", passed,
            "历史估值带分析完整" if passed else "历史估值带分析不完整",
            issues
        ))

    def check_cross_method_synthesis(self):
        """[Equity Report] 检查估值方法交叉验证"""
        text = self.soup.get_text()
        text_lower = text.lower()

        synthesis_signals = [
            "cross-method" in text_lower or "交叉验证" in text or "综合判断" in text,
            "valuation range" in text_lower or "估值区间" in text or "估值范围" in text,
            ("convergence" in text_lower or "收敛" in text or "一致" in text),
        ]

        passed = sum(synthesis_signals) >= 2
        self.results.append(CheckResult(
            "cross_method_synthesis", passed,
            "估值方法交叉验证完整" if passed else "估值部分缺少方法间交叉验证/综合判断叙述",
            [] if passed else ["估值部分需包含所有方法（可比、DCF、历史带）的综合判断叙述"]
        ))

    def check_chart_exhibits(self):
        """[Equity Report] 检查数据图表是否存在（C1-C5 from chart_generator.py）"""
        imgs = self.soup.find_all("img")
        svg_charts = [
            img for img in imgs
            if "image/svg+xml;base64" in (img.get("src", "") or "")
        ]

        # Exclude stock chart (typically PNG base64)
        chart_count = len(svg_charts)

        passed = chart_count >= 3  # At least 3 of 5 charts should render
        self.results.append(CheckResult(
            "chart_exhibits", passed,
            f"找到 {chart_count} 个SVG图表" + (
                "（≥3个，符合要求）" if passed else "（<3个，建议至少3/5个数据图表）"
            ),
            [] if passed else ["equity report应包含revenue/margin/market share/PE band/scenario等SVG图表"]
        ))

    def check_change_highlight(self):
        """检查同比/环比数据是否使用了 change-positive/change-negative 色块"""
        positive_spans = self.soup.find_all("span", class_="change-positive")
        negative_spans = self.soup.find_all("span", class_="change-negative")
        total = len(positive_spans) + len(negative_spans)
        passed = total >= 1
        self.results.append(CheckResult(
            "change_highlight_usage", passed,
            f"找到 {len(positive_spans)} 处正向高亮和 {len(negative_spans)} 处负向高亮" + (
                "" if passed else "（建议至少在同比/环比数据中使用 .change-positive/.change-negative 类）"
            ),
            []
        ))

    def check_page_balance(self, mode: str = "auto"):
        """页面美观度/平衡度检查：检测模块标题与内容是否可能被分页截断

        启发式规则：
        1. (Equity Report only) 大模块（>600字符）缺少 page-break-before 保护时提示
           — Tear Sheet 跳过此规则，因为3-5页紧凑布局中强制分页会导致空白页
        2. 投资逻辑模块（第一页核心模块）如果内容字符数 > 2500，警告（可能占满第一页，
           挤压后续模块空间）
        3. (Equity Report only) 相邻大模块（各>800字符）缺少分页保护时提示
           — Tear Sheet 跳过此规则
        4. exhibit-label 缺少 page-break-after 保护时警告（Exhibit标题可能被孤立）
        """
        issues = []
        details = []
        module_rows = self.soup.find_all("div", class_="module-row")
        is_tear_sheet = (mode == "tear_sheet")

        # 第一页核心模块不需要分页保护（它们本来就在第一页）
        first_page_modules = ["投资逻辑", "股价走势", "核心交易", "交易数据"]

        for i, module in enumerate(module_rows):
            title_el = module.find("div", class_="section-title")
            if not title_el:
                continue

            text = module.get_text(strip=True)
            char_count = len(text)
            title_text = title_el.get_text(strip=True)[:30]

            # 跳过第一页核心模块的分页保护检查
            is_first_page = any(kw in title_text for kw in first_page_modules)

            # 检查是否有分页保护
            style = module.get("style", "")
            has_page_break = "page-break-before" in style
            has_newpage_class = "module-newpage" in (module.get("class") or [])
            is_protected = has_page_break or has_newpage_class

            # 规则1：大模块缺少分页保护（Equity Report only）
            if char_count > 600 and not is_protected and not is_first_page:
                msg = (
                    f"模块 '{title_text}' 内容量 {char_count} 字符，缺少分页保护 "
                    f"（建议评估是否需要 style=\"page-break-before: always;\"）"
                )
                if is_tear_sheet:
                    details.append(msg + " [Tear Sheet：不强制分页，由空间感知规则控制]")
                else:
                    issues.append(msg)

            # 规则2：投资逻辑模块空间挤压检查（两个模式都检查）
            if "投资逻辑" in text and char_count > 2500:
                issues.append(
                    f"投资逻辑模块内容量 {char_count} 字符，可能占满第一页，"
                    f"导致后续模块被挤到第二页。建议精简至 2200 字符以内"
                )

            # 规则3：相邻大模块检查（Equity Report only）
            if i > 0 and char_count > 800:
                prev_module = module_rows[i - 1]
                prev_text = prev_module.get_text(strip=True)
                prev_style = prev_module.get("style", "")
                prev_has_break = "page-break-before" in prev_style
                prev_char_count = len(prev_text)
                if prev_char_count > 800 and not prev_has_break and not is_protected:
                    title_text = title_el.get_text(strip=True)[:30]
                    msg = (
                        f"模块 '{title_text}' 与前一个模块内容量均 > 800 字符，"
                        f"连续大模块缺少分页保护，可能导致页面拥挤"
                    )
                    if is_tear_sheet:
                        details.append(msg + " [Tear Sheet：允许自然流动]")
                    else:
                        issues.append(msg)

        # 规则4：Exhibit标题孤立检查
        # For Tear Sheets: CSS rule `.exhibit-label + * { page-break-before: avoid }`
        # already ensures exhibit labels follow their content — skip this check to avoid false positives
        if not is_tear_sheet:
            exhibit_labels = self.soup.find_all("div", class_="exhibit-label")
            for label in exhibit_labels:
                label_style = label.get("style", "")
                has_break_after = "page-break-after" in label_style
                if not has_break_after:
                    label_text = label.get_text(strip=True)[:40]
                    issues.append(
                        f"Exhibit标题 '{label_text}' 缺少 page-break-after 保护，"
                        f"可能在PDF中被孤立在页底（建议添加 style=\"page-break-after: avoid;\"）"
                    )

        passed = len(issues) == 0
        all_details = issues + details
        self.results.append(CheckResult(
            "page_balance", passed,
            "页面平衡度检查通过，无分页截断风险" if passed else
            f"发现 {len(issues)} 处页面平衡度问题",
            all_details if all_details else []
        ))


def print_results(results: List[CheckResult], use_json: bool = False):
    if use_json:
        output = {
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.passed),
                "failed": sum(1 for r in results if not r.passed),
            },
            "checks": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details,
                }
                for r in results
            ],
        }
        import json
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("研报结构预检结果")
        print("=" * 60)
        passed_count = sum(1 for r in results if r.passed)
        print(f"通过: {passed_count}/{len(results)}")
        print("-" * 60)
        for r in results:
            status = "[成立] 通过" if r.passed else "[不成立] 失败"
            print(f"{status} | {r.name}")
            print(f"       {r.message}")
            if r.details:
                for d in r.details:
                    print(f"       - {d}")
        print("=" * 60)
        if passed_count < len(results):
            print("建议：优先修复失败项后再进行人工 A/B/C 级检查。")
        else:
            print("所有结构检查通过，可进行下一步人工质量检查。")


def main():
    parser = argparse.ArgumentParser(description="研报结构自动化预检脚本")
    parser.add_argument("--html", type=str, required=True, help="报告 HTML 文件路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    parser.add_argument("--mode", choices=["tear_sheet", "equity_report", "auto"],
                       default="auto", help="报告模式 (default: auto-detect)")
    args = parser.parse_args()

    path = Path(args.html)
    if not path.exists():
        print(f"错误：文件不存在 {args.html}")
        sys.exit(1)

    html_content = path.read_text(encoding="utf-8")
    validator = ReportValidator(html_content)
    results = validator.run_all(mode=args.mode)
    print_results(results, use_json=args.json)

    # 如果有失败项，返回非零退出码
    if any(not r.passed for r in results):
        sys.exit(2)


if __name__ == "__main__":
    main()
