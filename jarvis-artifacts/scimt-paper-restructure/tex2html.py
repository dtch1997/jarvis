"""Minimal LaTeX -> HTML for the paper's own dialect (sections, figures, tables,
lists, acro acronyms, natbib cites, \\todo, the coincharter colour macros).

Not a general converter: it handles exactly what main.tex and its Sections use,
and falls back to leaving unknown commands' arguments as plain text. Output is an
HTML fragment; images become {{IMG:<basename>}} placeholders that build.py inlines.
"""
import re, sys, pathlib

# ---------------------------------------------------------------- helpers
def read(path):
    return pathlib.Path(path).read_text()

def strip_comments(s):
    out = []
    for line in s.split("\n"):
        i = 0; buf = []
        while i < len(line):
            c = line[i]
            if c == "\\" and i + 1 < len(line):
                buf.append(line[i:i+2]); i += 2; continue
            if c == "%":
                break
            buf.append(c); i += 1
        out.append("".join(buf))
    return "\n".join(out)

def balanced(s, i):
    """s[i] == '{' -> return (content, index after closing brace)."""
    assert s[i] == "{", s[i:i+20]
    depth = 0; j = i
    while j < len(s):
        if s[j] == "\\": j += 2; continue
        if s[j] == "{": depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0: return s[i+1:j], j + 1
        j += 1
    raise ValueError("unbalanced braces near " + s[i:i+40])

def optarg(s, i):
    """optional [..] at s[i]; returns (content or None, new index)."""
    if i < len(s) and s[i] == "[":
        j = s.index("]", i); return s[i+1:j], j + 1
    return None, i

def apply_cmd(s, name, fn, nargs=1, opt=False):
    """Replace every \\name{a}{b}.. with fn(args) (args already converted recursively by caller if desired)."""
    pat = "\\" + name
    out = []; i = 0
    while True:
        k = s.find(pat, i)
        if k < 0: out.append(s[i:]); break
        after = k + len(pat)
        # make sure we matched a whole command name (not \acp when looking for \ac)
        if after < len(s) and s[after].isalpha():
            out.append(s[i:after]); i = after; continue
        out.append(s[i:k])
        j = after
        while j < len(s) and s[j] == " ": j += 1
        o = None
        if opt: o, j = optarg(s, j)
        args = []
        for _ in range(nargs):
            while j < len(s) and s[j] in " \n": j += 1
            if j < len(s) and s[j] == "{":
                a, j = balanced(s, j); args.append(a)
            else:
                args.append(""); break
        out.append(fn(args, o))
        i = j
    return "".join(out)

# ---------------------------------------------------------------- acronyms
def parse_acros(preamble):
    acros = {}
    for m in re.finditer(r"\\DeclareAcronym\{(\w+)\}\{(.*?)\n\}", preamble, re.S):
        body = m.group(2)
        long = re.search(r"long=([^,\n]+)", body).group(1).strip()
        short = re.search(r"short=([^,\n]+)", body).group(1).strip()
        acros[m.group(1)] = (long, short)
    return acros

class Acro:
    def __init__(self, table): self.t = table; self.used = set()
    def expand(self, cmd, key):
        long, short = self.t.get(key, (key, key.upper()))
        plural = cmd.endswith("p")
        cap = cmd[0] == "A"
        base = cmd.lower().rstrip("p")
        L = long + ("s" if plural else ""); S = short + ("s" if plural else "")
        if cap: L = L[0].upper() + L[1:]
        full = base in ("acf", "acl") or (base == "ac" and key not in self.used)
        self.used.add(key)
        if base == "acs": return S
        if base == "acl": return L
        if full: return f"{L} ({S})"
        return S

# ---------------------------------------------------------------- citations
def load_bib(path):
    bib = {}
    if not pathlib.Path(path).exists(): return bib
    for m in re.finditer(r"@\w+\{([^,]+),(.*?)\n\}", read(path), re.S):
        key = m.group(1).strip(); body = m.group(2)
        au = re.search(r"author\s*=\s*[{\"](.*?)[}\"]\s*,?\n", body, re.S)
        yr = re.search(r"year\s*=\s*[{\"]?(\d{4})", body)
        if not au: continue
        authors = [a.strip() for a in re.split(r"\s+and\s+", au.group(1).replace("\n", " "))]
        def surname(a):
            return a.split(",")[0].strip() if "," in a else a.split()[-1]
        names = [surname(a) for a in authors]
        if len(names) == 1: txt = names[0]
        elif len(names) == 2: txt = f"{names[0]} and {names[1]}"
        else: txt = f"{names[0]} et al."
        txt = re.sub(r"[{}]", "", txt)
        bib[key] = (txt, yr.group(1) if yr else "n.d.")
    return bib

def cite_from_key(key):
    m = re.match(r"([a-z]+)(\d{4})", key)
    if not m: return (key, "")
    return (m.group(1).capitalize() + " et al.", m.group(2))

class Cites:
    def __init__(self, bib): self.bib = bib
    def one(self, key, mode):
        key = key.strip()
        a, y = self.bib.get(key) or cite_from_key(key)
        return f"{a} ({y})" if mode == "t" else f"{a}, {y}"
    def render(self, keys, mode):
        parts = [self.one(k, mode) for k in keys.split(",")]
        s = "; ".join(parts)
        return f'<span class="cite">{s}</span>' if mode == "t" else f'<span class="cite">({s})</span>'

# ---------------------------------------------------------------- converter
class Conv:
    def __init__(self, root, acros, bib):
        self.root = pathlib.Path(root); self.ac = Acro(acros); self.cites = Cites(bib)
        self.labels = {}      # label -> (kind, number)
        self.sec = [0, 0, 0]; self.fig = 0; self.tab = 0; self.fn = 0
        self.appendix = False; self.footnotes = []

    # ---- pass 1: numbering for labels (sections, figures, tables) in document order
    def prenumber(self, body):
        sec = [0, 0, 0]; fig = 0; tab = 0; app = False
        env_stack = []
        for m in re.finditer(r"\\(appendix)\b|\\(section|subsection|subsubsection)\*?\{|\\begin\{(figure|table)\}|\\label\{([^}]+)\}", body):
            if m.group(1): app = True; sec = [0, 0, 0]; continue
            if m.group(2):
                lvl = {"section": 0, "subsection": 1, "subsubsection": 2}[m.group(2)]
                sec[lvl] += 1
                for k in range(lvl + 1, 3): sec[k] = 0
                self._last = ("sec", self.secnum(sec, app)); continue
            if m.group(3):
                if m.group(3) == "figure": fig += 1; self._last = ("fig", str(fig))
                else: tab += 1; self._last = ("tab", str(tab))
                continue
            if m.group(4):
                self.labels[m.group(4)] = getattr(self, "_last", ("sec", "?"))
    @staticmethod
    def secnum(sec, app):
        first = chr(ord("A") + sec[0] - 1) if app else str(sec[0])
        parts = [first] + [str(x) for x in sec[1:] if x]
        # trim trailing zeros already excluded
        return ".".join(parts)

    def ref(self, label, kind_hint=None):
        kind, num = self.labels.get(label, ("?", "?"))
        word = {"sec": "§", "fig": "Figure ", "tab": "Table ", "?": ""}[kind]
        return f'<a class="xref" href="#{label}">{word}{num}</a>'

    # ---- inline conversion
    def inline(self, s):
        # protect escapes
        s = s.replace("\\%", "\x00PCT").replace("\\&", "&amp;").replace("\\_", "_").replace("\\#", "#").replace("\\$", "\x00DOL")
        s = s.replace("\\{", "\x00LB").replace("\\}", "\x00RB")
        # acronyms
        s = apply_cmd(s, "acp", lambda a, o: self.ac.expand("acp", a[0]))
        s = apply_cmd(s, "Acp", lambda a, o: self.ac.expand("Acp", a[0]))
        s = apply_cmd(s, "acf", lambda a, o: self.ac.expand("acf", a[0]))
        s = apply_cmd(s, "Acf", lambda a, o: self.ac.expand("Acf", a[0]))
        s = apply_cmd(s, "acs", lambda a, o: self.ac.expand("acs", a[0]))
        s = apply_cmd(s, "acl", lambda a, o: self.ac.expand("acl", a[0]))
        s = apply_cmd(s, "Ac", lambda a, o: self.ac.expand("Ac", a[0]))
        s = apply_cmd(s, "ac", lambda a, o: self.ac.expand("ac", a[0]))
        # cites
        s = apply_cmd(s, "citep", lambda a, o: self.cites.render(a[0], "p"), opt=True)
        s = apply_cmd(s, "citet", lambda a, o: self.cites.render(a[0], "t"), opt=True)
        s = apply_cmd(s, "cite", lambda a, o: self.cites.render(a[0], "p"), opt=True)
        # refs
        s = apply_cmd(s, "autoref", lambda a, o: self.ref(a[0]))
        s = re.sub(r"\\S\\ref\{([^}]+)\}", lambda m: self.ref(m.group(1)), s)
        s = re.sub(r"(Section|Appendix|Appendices|Figure|Figures|Table|Tables)~\\ref\{([^}]+)\}", lambda m: self.ref(m.group(2)), s)
        s = apply_cmd(s, "ref", lambda a, o: self.ref(a[0]))
        s = apply_cmd(s, "label", lambda a, o: "")
        # todo / colour
        s = apply_cmd(s, "todo", lambda a, o: f'<span class="todo">{self.inline(a[0])}</span>')
        s = apply_cmd(s, "textcolor", lambda a, o: f'<span class="todo">{self.inline(a[1])}</span>', nargs=2)
        # coincharter macros
        s = re.sub(r"\\charter\b\\xspace|\\charter\b", '<b class="ch">Charter</b>', s)
        s = re.sub(r"\\coin\b\\xspace|\\coin\b", '<b class="co">Coin</b>', s)
        s = re.sub(r"\\control\b", '<b class="ctl">Control</b>', s)
        # text formatting
        for cmd, tag in (("textbf", "b"), ("emph", "em"), ("textit", "em"), ("texttt", "code"), ("textsuperscript", "sup"), ("mathbf", "b"), ("small", "span")):
            s = apply_cmd(s, cmd, lambda a, o, tag=tag: f"<{tag}>{self.inline(a[0])}</{tag}>")
        s = apply_cmd(s, "footnote", lambda a, o: self.footnote(a[0]))
        s = apply_cmd(s, "url", lambda a, o: f'<a href="{a[0]}">{a[0]}</a>')
        s = apply_cmd(s, "mathrm", lambda a, o: a[0])
        s = apply_cmd(s, "mathtt", lambda a, o: f"<code>{a[0]}</code>")
        s = apply_cmd(s, "operatorname", lambda a, o: a[0])
        s = apply_cmd(s, "text", lambda a, o: a[0])
        # math: strip $ and a few symbols
        s = re.sub(r"\$\$(.*?)\$\$", lambda m: f'<span class="math">{self.math(m.group(1))}</span>', s, flags=re.S)
        s = re.sub(r"\\\[(.*?)\\\]", lambda m: f'<div class="math">{self.math(m.group(1))}</div>', s, flags=re.S)
        s = re.sub(r"\$(.*?)\$", lambda m: f'<span class="math">{self.math(m.group(1))}</span>', s, flags=re.S)
        # misc
        s = s.replace("\\,", "&thinsp;").replace("\\ ", " ").replace("\\@", "")
        s = s.replace("\\S", "§").replace("\\dagger", "†").replace("\\ldots", "…").replace("\\dots", "…")
        s = s.replace("\\xspace", "").replace("\\linewidth", "").replace("\\centering", "").replace("\\noindent", "")
        s = re.sub(r"\\(?:vspace|hspace)\{[^}]*\}", "", s)
        s = re.sub(r"\\(?:bigskip|medskip|smallskip|newpage|clearpage|maketitle)\b", "", s)
        s = s.replace("``", "“").replace("''", "”").replace("`", "‘").replace("---", "—").replace("--", "–")
        s = s.replace("~", "&nbsp;")
        s = re.sub(r"\\\\(\[[^\]]*\])?", "<br>", s)
        s = s.replace("\x00PCT", "%").replace("\x00DOL", "$").replace("\x00LB", "{").replace("\x00RB", "}")
        # leftover simple commands: drop the backslash-name, keep braces content
        s = re.sub(r"\\[A-Za-z]+\*?", "", s)
        s = s.replace("{", "").replace("}", "")
        return s

    def math(self, m):
        m = m.replace("\\rightarrow", "→").replace("\\wedge", "∧").replace("\\subset", "⊂").replace("\\parallel", "∥")
        m = m.replace("\\mathrm", "").replace("\\mathbf", "").replace("\\texttt", "").replace("\\text", "").replace("\\,", " ")
        m = m.replace("\\times", "×").replace("\\%", "%").replace("\\_", "_")
        m = re.sub(r"\^\{([^}]*)\}", r"<sup>\1</sup>", m); m = re.sub(r"\^(\w)", r"<sup>\1</sup>", m)
        m = re.sub(r"_\{([^}]*)\}", r"<sub>\1</sub>", m); m = re.sub(r"_(\w)", r"<sub>\1</sub>", m)
        m = re.sub(r"\\[A-Za-z]+", "", m)
        return m.replace("{", "").replace("}", "").strip()

    def footnote(self, text):
        self.fn += 1; n = self.fn
        self.footnotes.append(f'<li id="fn{n}">{self.inline(text)}</li>')
        return f'<sup class="fnref"><a href="#fn{n}">{n}</a></sup>'

    # ---- block conversion
    def blocks(self, s):
        out = []
        i = 0
        pat = re.compile(r"\\begin\{(figure|table|enumerate|itemize|quote|abstract)\}(\[[^\]]*\])?")
        while True:
            m = pat.search(s, i)
            if not m: out.append(self.paragraphs(s[i:])); break
            out.append(self.paragraphs(s[i:m.start()]))
            env = m.group(1)
            end = s.index(f"\\end{{{env}}}", m.end())
            inner = s[m.end():end]
            out.append(getattr(self, "env_" + env)(inner))
            i = end + len(f"\\end{{{env}}}")
        return "".join(out)

    def paragraphs(self, s):
        # section headings and \paragraph split the text
        parts = re.split(r"(\\(?:section|subsection|subsubsection)\*?\{|\\paragraph\{|\\appendix\b)", s)
        out = []; i = 0
        # rebuild: parts alternates text, marker, text, marker...
        buf = parts[0]
        out.append(self.paras(buf))
        j = 1
        while j < len(parts):
            marker, rest = parts[j], parts[j+1]; j += 2
            if marker.startswith("\\appendix"):
                self.appendix = True; self.sec = [0, 0, 0]
                out.append('<div class="appendix-rule"><span>Appendix</span></div>')
                out.append(self.paras(rest)); continue
            title, k = balanced("{" + rest, 0)
            rest = rest[k-1:]
            # label right after heading
            lab = re.match(r"\s*\\label\{([^}]+)\}", rest)
            anchor = ""
            if lab: anchor = f' id="{lab.group(1)}"'; rest = rest[lab.end():]
            if marker.startswith("\\paragraph"):
                # run-in heading merged with the following paragraph
                first, _, more = rest.lstrip("\n").partition("\n\n")
                out.append(f'<p{anchor}><b class="runin">{self.inline(title)}</b> {self.inline(first.strip())}</p>')
                out.append(self.paras(more))
            else:
                lvl = {"\\section{": 0, "\\section*{": -1, "\\subsection{": 1, "\\subsubsection{": 2}[marker]
                if lvl >= 0:
                    self.sec[lvl] += 1
                    for q in range(lvl + 1, 3): self.sec[q] = 0
                    num = self.secnum(self.sec, self.appendix)
                    tag = "h2" if lvl == 0 else "h3" if lvl == 1 else "h4"
                    out.append(f'<{tag}{anchor}><span class="secnum">{num}</span>{self.inline(title)}</{tag}>')
                else:
                    out.append(f'<h2{anchor}>{self.inline(title)}</h2>')
                out.append(self.paras(rest))
        return "".join(out)

    def paras(self, s):
        out = []
        for chunk in re.split(r"\n\s*\n", s):
            t = chunk.strip()
            if not t: continue
            if re.fullmatch(r"(\\(?:centering|vspace\{[^}]*\}|small|bibliography\{[^}]*\}|bibliographystyle\{[^}]*\}|include\{[^}]*\}|input\{[^}]*\})\s*)+", t): continue
            h = self.inline(t)
            if not h.strip(): continue
            out.append(f"<p>{h}</p>")
        return "\n".join(out)

    def env_abstract(self, inner):
        return f'<section class="abstract"><h2>Abstract</h2>{self.paras(inner)}</section>'
    def env_quote(self, inner):
        return f"<blockquote>{self.paras(inner)}</blockquote>"
    def env_enumerate(self, inner): return self.listenv(inner, "ol")
    def env_itemize(self, inner): return self.listenv(inner, "ul")
    def listenv(self, inner, tag):
        items = re.split(r"\\item\b", inner)[1:]
        return f"<{tag}>" + "".join(f"<li>{self.inline(it.strip())}</li>" for it in items) + f"</{tag}>"

    def env_figure(self, inner):
        self.fig += 1
        cap = re.search(r"\\caption\{", inner)
        caption = ""
        if cap:
            c, _ = balanced(inner, cap.end() - 1); caption = self.inline(c)
        lab = re.search(r"\\label\{([^}]+)\}", inner)
        anchor = f' id="{lab.group(1)}"' if lab else ""
        imgs = []
        for m in re.finditer(r"\\includegraphics(\[[^\]]*\])?\{([^}]+)\}", inner):
            base = pathlib.Path(m.group(2)).stem
            imgs.append(f'<img src="{{{{IMG:{base}}}}}" alt="{base}">')
        for m in re.finditer(r"\\figph\{([^}]+)\}", inner):
            imgs.append(f'<div class="figph">figure placeholder: {m.group(1).replace(chr(92), "")}</div>')
        if "\\input{Tikz_Figs" in inner:
            imgs.append('<div class="figph">tikz figure (results_preview)</div>')
        body = "".join(imgs)
        return f'<figure{anchor}>{body}<figcaption><b>Figure {self.fig}.</b> {caption}</figcaption></figure>'

    def env_table(self, inner):
        self.tab += 1
        cap = re.search(r"\\caption\{", inner); caption = ""
        if cap:
            c, _ = balanced(inner, cap.end() - 1); caption = self.inline(c)
        lab = re.search(r"\\label\{([^}]+)\}", inner)
        anchor = f' id="{lab.group(1)}"' if lab else ""
        tm = re.search(r"\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}", inner, re.S)
        rows_html = ""
        if tm:
            body = re.sub(r"\\(?:toprule|midrule|bottomrule|hline)", "", tm.group(1))
            rows = [r for r in re.split(r"\\\\", body) if r.strip()]
            header_done = False
            for r in rows:
                cells = [self.inline(c.strip()) for c in r.split("&")]
                tag = "th" if not header_done else "td"
                rows_html += "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"
                header_done = True
        return f'<figure class="table"{anchor}><figcaption><b>Table {self.tab}.</b> {caption}</figcaption><div class="tbl"><table>{rows_html}</table></div></figure>'

    # ---- document
    def convert(self, main):
        src = read(self.root / main)
        pre, _, body = src.partition("\\begin{document}")
        body = body.split("\\end{document}")[0]
        # inline inputs
        def inl(m):
            p = self.root / (m.group(2) + ("" if m.group(2).endswith(".tex") else ".tex"))
            return read(p) if p.exists() else ""
        body = re.sub(r"\\(input|include)\{([^}]+)\}", inl, body)
        body = strip_comments(body)
        title = re.search(r"\\title\{([^}]+)\}", pre)
        self.prenumber(body)
        html = self.blocks(body)
        notes = f'<section class="footnotes"><h2>Notes</h2><ol>{"".join(self.footnotes)}</ol></section>' if self.footnotes else ""
        return f'<h1 class="paper-title">{title.group(1) if title else ""}</h1>' + html + notes

def main():
    root = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2])
    pre = read(root / "main.tex").partition("\\begin{document}")[0]
    conv = Conv(root, parse_acros(pre), load_bib(root / "refs.bib"))
    out.write_text(conv.convert("main.tex"))
    print(f"wrote {out} ({out.stat().st_size/1e3:.0f} KB), {conv.fig} figures, {conv.tab} tables, {len(conv.footnotes)} footnotes")

if __name__ == "__main__":
    main()
