"""Layout-only regression checks for manuscript table generation."""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from table_layout import format_table


def fixture(label, spec):
    return (r'\begin{table*}[t]'+'\n'+r'\caption{Same caption}'+'\n'
            +r'\label{'+label+'}\n'+r'\setlength{\tabcolsep}{5pt}'+'\n'
            +r'\footnotesize'+'\n'+r'\begin{tabular}{@{}'+spec+r'@{}}'+'\n'
            +r'\toprule'+'\n'+r'A & B & C \\'+'\n'+r'\midrule'+'\n'
            +r'1 & 9/12 & 118.520 \\'+'\n'+r'\bottomrule'+'\n'
            +r'\end{tabular}'+'\n'+r'\end{table*}')


def test_profile_float_becomes_single_column_with_wrapped_ids():
    result = format_table(fixture('tab:required-profiles','lrrl'))
    assert r'\begin{table}[t]' in result
    assert r'\begin{tabularx}{\linewidth}' in result


def test_development_table_fits_one_column_with_stacked_headers():
    source = fixture('tab:required-profile-results','lrlrr').replace('A & B & C',
        'Profile & Required items & Split & ADP complete & Local complete')
    result = format_table(source)
    assert r'\begin{table}[t]' in result
    assert r'\shortstack[r]{Required\\items}' in result
    assert r'\begin{tabular*}{\linewidth}' in result


def test_dense_statistics_remain_full_width_without_resizing():
    for label in ['tab:depth-sensitivity','tab:paired-aggregate','tab:required-paired']:
        source = fixture(label,'lrr')
        result = format_table(source)
        assert r'\begin{table*}[t]' in result
        assert r'\begin{tabular*}{\linewidth}' in result
        assert r'\resizebox' not in result
        assert r'\footnotesize' in result
        assert re.search(r'\\midrule(.*?)\\bottomrule',source,re.S).group(1) == re.search(r'\\midrule(.*?)\\bottomrule',result,re.S).group(1)


def test_formatting_is_idempotent_and_unrelated_tables_unchanged():
    for label,spec in [('tab:required-profiles','lrrl'),('tab:required-profile-results','lrlrr'),('tab:required-paired','llrrlrr')]:
        once = format_table(fixture(label,spec))
        assert format_table(once) == once
    other = fixture('tab:required-objective','llr')
    assert format_table(other) == other
