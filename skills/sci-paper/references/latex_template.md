# LaTeX Template Reference

When generating PDF output, use a proper LaTeX template to match the reference
style. The ResNet paper uses the CVPR/ICCV conference style (IEEEtran-derived).

## Recommended LaTeX Document Classes

| Venue | Document Class | Options |
|-------|---------------|---------|
| CVPR/ICCV/ECCV | `\documentclass[10pt,twocolumn]{article}` + cvpr.sty | 10pt, twocolumn |
| NeurIPS | `\documentclass{article}` + neurips_*.sty | 10pt, onecolumn |
| ICML | `\documentclass{article}` + icml*.sty | 10pt, onecolumn |
| ICLR | `\documentclass[10pt,twocolumn]{article}` | 10pt, twocolumn |
| General | `\documentclass[10pt,twocolumn]{article}` + geometry | 10pt, twocolumn |

## Minimal Double-Column Template

```latex
\documentclass[10pt,twocolumn]{article}

% Page geometry matching CVPR/ICCV style
\usepackage[letterpaper, margin=0.75in, top=0.75in, bottom=1.0in]{geometry}
\setlength{\columnsep}{0.25in}

% Essential packages
\usepackage{times}          % NimbusRomNo9L equivalent
\usepackage{mathptmx}       % Times math fonts
\usepackage{amsmath,amssymb} % Math environments
\usepackage{graphicx}        % Figures
\usepackage[dvipsnames]{xcolor}  % Colors
\usepackage{booktabs}        % Professional tables
\usepackage{caption}         % Caption formatting
\usepackage{subcaption}      % Subfigures
\usepackage{multirow}        % Multi-row table cells
\usepackage{algorithm}       % Algorithm environments
\usepackage{algorithmic}     % Algorithm pseudocode
\usepackage{hyperref}        % Hyperlinks (dark blue)
\hypersetup{colorlinks=true, linkcolor=blue, citecolor=blue, urlcolor=blue}

% Line spacing
\usepackage{setspace}
\setstretch{1.0}

% Paragraph settings
\setlength{\parindent}{1em}
\setlength{\parskip}{0pt}

% Section formatting
\usepackage{titlesec}
\titleformat{\section}{\normalfont\large\bfseries}{\thesection.}{0.5em}{}
\titleformat{\subsection}{\normalfont\normalsize\bfseries}{\thesubsection}{0.5em}{}
\titlespacing*{\section}{0pt}{12pt}{6pt}
\titlespacing*{\subsection}{0pt}{6pt}{3pt}

% Caption formatting (figures below, tables above)
\captionsetup[figure]{font=small, labelfont=bf, labelsep=period, belowskip=6pt, aboveskip=6pt}
\captionsetup[table]{font=small, labelfont=bf, labelsep=period, belowskip=6pt, aboveskip=6pt}

\begin{document}

% Title
\title{\Large\bfseries Paper Title Goes Here}
\author{Author One$^1$ \quad Author Two$^1$ \quad Author Three$^2$ \\
        $^1$Institution One \quad $^2$Institution Two}
\date{}
\maketitle

% Abstract (single column)
\begin{abstract}
Abstract text goes here. One paragraph, ~150 words. Must cover:
background, problem, method, key results, significance.
\end{abstract}

% Main body (double column)
\section{Introduction}\label{sec:intro}
Introduction text...

\section{Related Work}\label{sec:related}
Related work text...

\section{Method}\label{sec:method}
\subsection{Core Formulation}\label{sec:formulation}
Formulation text with equations:
\begin{equation}\label{eq:residual}
y = \mathcal{F}(x, \{W_i\}) + x.
\end{equation}

\subsection{Key Mechanism}\label{sec:mechanism}
Mechanism text...

\subsection{Architecture}\label{sec:architecture}
Architecture text with figure reference: see Fig.~\ref{fig:arch}.

\begin{figure}[t]
\centering
\includegraphics[width=\linewidth]{figure_architecture.pdf}
\caption{Architecture diagram caption goes here.}
\label{fig:arch}
\end{figure}

\subsection{Implementation Details}\label{sec:implementation}
Implementation text...

\section{Experiments}\label{sec:experiments}
\subsection{Main Benchmark}\label{sec:main}
Main results with table reference: see Table~\ref{tab:results}.

\begin{table}[t]
\centering
\caption{Table caption goes ABOVE the table.}
\label{tab:results}
\begin{tabular}{lcc}
\toprule
Method & Metric1 & Metric2 \\
\midrule
Baseline & 28.54 & 10.02 \\
Ours & \textbf{21.43} & \textbf{5.71} \\
\bottomrule
\end{tabular}
\end{table}

\subsection{Analysis}\label{sec:analysis}
Analysis text...

\subsection{Extension}\label{sec:extension}
Extension text...

\section{Conclusion}\label{sec:conclusion}
Conclusion text...

% References
\bibliographystyle{ieee_fullname}
\bibliography{references}

\end{document}
```

## Key LaTeX Packages for Paper Writing

| Package | Purpose |
|---------|---------|
| `times` / `mathptmx` | Times Roman body + math fonts (matching reference) |
| `amsmath`, `amssymb` | Math environments and symbols |
| `graphicx` | Include figures |
| `booktabs` | Professional table formatting (\toprule, \midrule, \bottomrule) |
| `caption` | Figure/table caption formatting |
| `subcaption` | Subfigures with (a), (b), (c) labels |
| `multirow` | Multi-row cells in tables |
| `algorithm`, `algorithmic` | Algorithm pseudocode |
| `xcolor` | Colors for figures |
| `pgfplots` / `tikz` | Vector graphics and plots |
| `bibtex` / `natbib` | Bibliography management |
| `hyperref` | Hyperlinks and cross-references |

## Figure Generation with pgfplots

For publication-quality line plots matching the reference style:

```latex
\usepackage{pgfplots}
\pgfplotsset{compat=1.17}
\pgfplotsset{
    every axis/.append style={
        font=\footnotesize,
        line width=0.8pt,
        tick style={line width=0.6pt},
        major tick length=2pt,
        minor tick length=1pt,
        grid=none,
    },
    legend style={
        font=\footnotesize,
        draw=none,
        fill=none,
    },
}
```

## Table Best Practices in LaTeX

```latex
% Professional table with booktabs
\begin{table}[t]
\centering
\caption{Error rates (\%) on ImageNet validation.}
\label{tab:main}
\small  % or \footnotesize for dense tables
\begin{tabular}{@{}lcc@{}}
\toprule
Model & top-1 err. & top-5 err. \\
\midrule
VGG-16 & 28.07 & 9.33 \\
ResNet-34 & 25.03 & 7.76 \\
ResNet-152 & \textbf{21.43} & \textbf{5.71} \\
\bottomrule
\end{tabular}
\end{table}
```

## Bibliography Style

Use `ieee_fullname.bst` or `ieeetr.bst` for numbered references:

```bibtex
@inproceedings{he2016deep,
  title={Deep residual learning for image recognition},
  author={He, Kaiming and Zhang, Xiangyu and Ren, Shaoqing and Sun, Jian},
  booktitle={CVPR},
  pages={770--778},
  year={2016}
}
```

## Compilation Command

```bash
pdflatex paper.tex
bibtex paper
pdflatex paper.tex
pdflatex paper.tex  # Final pass for cross-references
```
