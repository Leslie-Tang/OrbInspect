"""IEEE table geometry policies; preserve captions, values and font sizes."""
from __future__ import annotations

import re


def format_table(source: str) -> str:
    """Use one column for compact profile tables and align wide statistics."""
    match = re.search(r'\\label\{([^}]+)\}', source)
    if not match:
        return source
    label = match.group(1)
    narrow = label in {'tab:required-profiles', 'tab:required-profile-results'}
    if narrow:
        source = source.replace(r'\begin{table*}', r'\begin{table}')
        source = source.replace(r'\end{table*}', r'\end{table}')
    if label == 'tab:required-profiles':
        source = source.replace(r'\setlength{\tabcolsep}{5pt}', r'\setlength{\tabcolsep}{4pt}')
        source = source.replace(r'\begin{tabular}{@{}lrrl@{}}',
            r'\begin{tabularx}{\linewidth}{@{}lr>{\centering\arraybackslash}p{2.6em}>{\raggedright\arraybackslash}X@{}}')
        source = source.replace(r'\end{tabular}', r'\end{tabularx}')
        source = source.replace('Slab counts', r'\shortstack{Slab\\counts}')
    elif label == 'tab:required-profile-results':
        source = source.replace('Required items', r'\shortstack[r]{Required\\items}')
        source = source.replace('ADP complete', r'\shortstack[r]{ADP\\complete}')
        source = source.replace('Local complete', r'\shortstack[r]{Local\\complete}')
        source = stretch(source, 'lrlrr')
    elif label in {'tab:depth-sensitivity', 'tab:paired-aggregate', 'tab:required-paired'}:
        spec = re.search(r'\\begin\{tabular\}\{@\{\}([lcr]+)@\{\}\}', source)
        if spec:
            source = stretch(source, spec.group(1))
    return source


def stretch(source: str, spec: str) -> str:
    """Distribute intercolumn space within the current float, without scaling."""
    source = source.replace(r'\begin{tabular}{@{}'+spec+r'@{}}',
        r'\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}'+spec+r'@{}}')
    return source.replace(r'\end{tabular}', r'\end{tabular*}')
