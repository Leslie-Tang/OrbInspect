#!/usr/bin/env python3
"""Check editable labels with draw.io's current MathJax SVG renderer.

Runs a private headless browser profile, without touching any existing browser
session. The inspected content is the generated draw.io HTML and LaTeX itself.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'output/figure_notation_aligned_20260908'
TMP = ROOT/'tmp/pdfs/notation_math_20260908'
CHROME = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    pieces = []
    for stem in ['A_integrated', 'B1_overview', 'B2_adp_mechanism']:
        model = ET.parse(OUT/(stem+'.drawio')).find('.//mxGraphModel')
        assert model.get('math') == '1'
        for cell in model.findall('.//mxCell'):
            if not cell.get('notationSource'):
                continue
            st = dict(p.split('=', 1) for p in cell.get('style').split(';') if '=' in p)
            g = cell.find('mxGeometry')
            ident = stem+':'+cell.get('id')
            w, h = float(g.get('width')), float(g.get('height'))
            color = st.get('fontColor', '#000000')
            fill = '#303E44' if color.upper() == '#FFFFFF' else '#FFFFFF'
            pieces.append(f'<section><small>{html.escape(ident)}</small><div class="label" '
                f'data-id="{ident}" data-width="{w}" data-height="{h}" '
                f'style="width:{w}px;height:{h}px;font-size:{st["fontSize"]}px;'
                f'font-weight:{700 if int(st.get("fontStyle","0"))&1 else 400};'
                f'color:{color};background:{fill}">{cell.get("value")}</div></section>')
    header = '''<!doctype html><html><head><meta charset="utf-8">
<style>body{font-family:Arial,sans-serif;margin:20px}section{margin:12px 0}
.label{display:flex;align-items:center;justify-content:center;white-space:nowrap;
border:1px solid #ccc}.label>div{flex-shrink:0}small{font:12px Arial;color:#777}
</style><script>
window.MathJax={loader:{load:['output/svg','input/tex','input/asciimath','ui/safe','[tex]/html'],
paths:{fonts:'https://app.diagrams.net/math4/es5/fonts'}},output:{font:'mathjax-tex'},
startup:{pageReady:()=>MathJax.startup.defaultPageReady().then(()=>{
let labels=Array.from(document.querySelectorAll('.label')).map(e=>{
let b=e.getBoundingClientRect(),i=e.firstElementChild.getBoundingClientRect();
let glyphs=Array.from(e.querySelectorAll('mjx-container')).map(m=>m.getBoundingClientRect());
let errors=Array.from(e.querySelectorAll('[data-mml-node="merror"],mjx-merror')).length;
return {id:e.dataset.id,width:+e.dataset.width,height:+e.dataset.height,
rendered_width:i.width,rendered_height:i.height,math_count:glyphs.length,errors,
overflow:Math.max(0,i.width-(+e.dataset.width),i.height-(+e.dataset.height))};});
document.getElementById('result').textContent=JSON.stringify({status:'complete',
renderer:'draw.io math4/es5 MathJax SVG / mathjax-tex',labels});
document.documentElement.dataset.qa='complete';})}};
</script><script defer src="https://app.diagrams.net/math4/es5/startup.js"></script>
</head><body><pre id="result">pending</pre>'''
    source = TMP/'math_labels.html'
    source.write_text(header+'\n'.join(pieces)+'</body></html>')
    with tempfile.TemporaryDirectory(prefix='orbinspect-math-', dir=TMP) as profile:
        cmd = [str(CHROME), '--headless', '--disable-gpu', '--no-first-run',
               '--no-default-browser-check', '--user-data-dir='+profile,
               '--virtual-time-budget=18000', '--dump-dom', source.as_uri()]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=55)
    (TMP/'browser_stderr.txt').write_text(result.stderr)
    match = re.search(r'<pre id="result">(.*?)</pre>', result.stdout, re.S)
    assert match and match[1] != 'pending', 'Browser math rendering did not complete'
    report = json.loads(html.unescape(match[1]))
    assert not any(x['errors'] for x in report['labels']), 'MathJax syntax error'
    report['overflow_labels'] = [x for x in report['labels'] if x['overflow'] > 1]
    (TMP/'browser_math_QA.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'status': report['status'], 'label_count': len(report['labels']),
                      'math_count': sum(x['math_count'] for x in report['labels']),
                      'syntax_errors': sum(x['errors'] for x in report['labels']),
                      'overflow_labels': report['overflow_labels']}, indent=2))


if __name__ == '__main__':
    main()
