"""Copy measures drafted in a .dax file into _Measures.tmdl.

    py -3 scripts/add_measures.py my-new-measures.dax

The TMDL is the single source and what Power BI loads; the .dax file is only a draft. Each block is
comment lines, then "Name =" and the expression, separated by blank lines. Comment lines
become the measure description (///), except "// @format X", which becomes formatString.
Blocks that are only comments (section headers) are skipped.

Re-running is safe: a measure that already exists is replaced in place, a new one is
added before the table's column. lineageTags are derived from the measure name, so the
same measure always gets the same tag. Close Power BI Desktop first.
"""
import os, re, sys, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
TMDL = os.path.join(HERE, "..", "MaximoPowerBI.SemanticModel", "definition", "tables", "_Measures.tmdl")
NS = uuid.UUID("6f1c2d3e-0000-4000-8000-4d6178696d6f")  # fixed namespace for the tags


def parse(path):
    text = open(path, encoding="utf-8").read().replace("\r\n", "\n")
    out = []
    for block in re.split(r"\n\s*\n", text):
        lines = block.strip("\n").split("\n")
        i = next((k for k, l in enumerate(lines) if not l.startswith("//")), None)
        if i is None:
            continue
        head = re.match(r"^(.+?) =(.*)$", lines[i])
        if not head:
            sys.exit(f"cannot read measure header: {lines[i]!r}")
        doc, fmt = [], None
        for l in lines[:i]:
            if l.startswith("// @format "):
                fmt = l[len("// @format "):].strip()
            elif not l.startswith("// ===") and not l.startswith("// ---"):
                doc.append(l[2:].strip() if l.startswith("// ") or l == "//" else l[2:])
        body = ([head.group(2).strip()] if head.group(2).strip() else []) + lines[i + 1:]
        out.append((head.group(1).strip(), doc, fmt, body))
    return out


def to_tmdl(name, doc, fmt, body):
    q = f"'{name}'" if re.search(r"[^A-Za-z0-9_]", name) else name
    t = [f"\t/// {d}".rstrip() for d in doc]
    if len(body) == 1:
        t.append(f"\tmeasure {q} = {body[0]}")
    else:
        t.append(f"\tmeasure {q} =")
        t += [f"\t\t\t{l}".rstrip() if l.strip() else "" for l in body]
    if fmt:
        t.append(f"\t\tformatString: {fmt}")
    t.append(f"\t\tlineageTag: {uuid.uuid5(NS, name)}")
    return t


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    measures = parse(sys.argv[1])
    lines = open(TMDL, encoding="utf-8").read().replace("\r\n", "\n").split("\n")
    added = replaced = 0
    for name, doc, fmt, body in measures:
        block = to_tmdl(name, doc, fmt, body)
        q = re.escape(f"'{name}'" if re.search(r"[^A-Za-z0-9_]", name) else name)
        start = next((k for k, l in enumerate(lines) if re.match(rf"^\tmeasure {q} =", l)), None)
        if start is not None:
            # replace: back up over its /// lines, forward to the next blank line
            s = start
            while s > 0 and lines[s - 1].startswith("\t///"):
                s -= 1
            e = start
            while e < len(lines) and lines[e].strip():
                e += 1
            lines[s:e] = block
            replaced += 1
        else:
            col = next(k for k, l in enumerate(lines) if l.startswith("\tcolumn "))
            lines[col:col] = block + [""]
            added += 1
    with open(TMDL, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write("\n".join(lines))
    print(f"{len(measures)} measures from {sys.argv[1]}: {added} added, {replaced} replaced -> {os.path.normpath(TMDL)}")


if __name__ == "__main__":
    main()
