"""Verify the scoped published-literature revision without touching evidence."""
from pathlib import Path
import re

import pytest

PAPER = Path(__file__).resolve().parents[3] / 'OrbInspectLatex'
BACKUP = PAPER / 'archive/references_expansion_20260908'
SCENARIO_KEYS = {
    'kimura2000inspection', 'flores2014review', 'williams2002inspection',
    'maestrini2022guidance', 'tweddle2016facility', 'wang2024inspection',
    'hu2021learning', 'tian2024proximity', 'vanwijk2024inspection',
}
METHOD_KEYS = {
    'bertsekas1997combinatorial', 'bertsekas2005survey',
    'bertsekas2017iterations', 'kiumarsi2018survey', 'ames2017barrier',
    'wabersich2023predictive', 'nemhauser1978submodular',
}


def uncomment(text):
    return re.sub(r'(?<!\\)%[^\n]*', '', text)


def entries(text):
    """Split the repository's brace-formatted BibTeX records by entry headers."""
    return {match.group(2): (match.group(1), match.group(3))
            for match in re.finditer(
                r'@(\w+)\{([^,]+),(.*?)(?=\n@|\Z)', text, re.S)}


def test_bibliography_has_no_missing_unused_duplicate_or_preprint_entries():
    bib = (PAPER / 'references.bib').read_text()
    records = entries(bib)
    assert len(records) == len(re.findall(r'^@', bib, re.M)) == 33
    source = '\n'.join((PAPER / file).read_text() for file in
                       ['main.tex', 'sections/required_target_study.tex',
                        'sections/ros_verification_results.tex'])
    cited = {key.strip() for group in
             re.findall(r'\\cite(?:\[[^\]]*\])?\{([^}]+)\}', uncomment(source))
             for key in group.split(',')}
    assert cited == records.keys()
    assert not re.search(r'arxiv|archivePrefix|eprint\s*=', bib, re.I)
    dois = re.findall(r'\bdoi\s*=\s*\{([^}]+)\}', bib, re.I)
    assert len(dois) == len(set(doi.lower() for doi in dois))


def test_added_references_balance_scenario_and_methods_and_are_published():
    current = entries((PAPER / 'references.bib').read_text())
    before = entries((BACKUP / 'references.bib').read_text())
    assert current.keys() - before.keys() == SCENARIO_KEYS | METHOD_KEYS
    assert before.keys() - current.keys() == {'ogri2025switched'}
    assert len(SCENARIO_KEYS) == 9 and len(METHOD_KEYS) == 7
    ieee_transactions = 0
    for key in SCENARIO_KEYS | METHOD_KEYS:
        kind, body = current[key]
        assert kind == 'article'
        for field in ('journal', 'volume', 'pages', 'year', 'doi'):
            assert re.search(r'\b' + field + r'\s*=\s*\{[^}]+\}', body)
        ieee_transactions += 'IEEE Transactions' in body
    assert ieee_transactions == 7


@pytest.mark.parametrize('name', ['main.tex', 'required_target_study.tex'])
def test_equations_proofs_algorithms_and_figures_are_unchanged(name):
    before = (BACKUP / name).read_text()
    after_path = PAPER / name if name == 'main.tex' else PAPER / 'sections' / name
    after = after_path.read_text()
    environments = ('equation', 'equation*', 'align', 'align*', 'figure',
                    'figure*', 'table', 'table*', 'algorithm', 'IEEEproof',
                    'proposition', 'theorem')
    for environment in environments:
        pattern = (r'\\begin\{' + re.escape(environment) + r'\}.*?'
                   r'\\end\{' + re.escape(environment) + r'\}')
        assert re.findall(pattern, before, re.S) == re.findall(pattern, after, re.S)
    assert re.findall(r'\\input\{[^}]+\}', before) == re.findall(
        r'\\input\{[^}]+\}', after)


def test_approved_figure_manifest_is_unchanged():
    assert (PAPER / 'figures/manifest.json').read_bytes() == (
        BACKUP / 'manifest.json').read_bytes()
