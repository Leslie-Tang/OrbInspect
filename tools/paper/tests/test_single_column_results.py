"""Guard the final-size result figures against data or layout regression."""
from pathlib import Path
import importlib.util
import json
import re

import matplotlib.pyplot as plt
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('result_figures', ROOT/'OrbInspectLatex/scripts/generate_result_figures.py')
figures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(figures)


@pytest.fixture(scope='module')
def evidence():
    return figures.load_evidence()


def test_frozen_cohorts_and_original_statistics(evidence):
    assert [evidence['cohorts'][s]['joint_success_n'] for s in ('test', 'ood')] == [43, 8]
    assert evidence['matched_effort']['n'] == 43
    assert evidence['success']['test'][figures.ADP] == {'complete': 43, 'total': 50}
    assert evidence['success']['ood'][figures.ADP] == {'complete': 9, 'total': 30}


def test_every_performance_point_and_band_is_retained(evidence):
    figures.style()
    fig = figures.plot_performance(evidence)
    for i, split in enumerate(('test', 'ood')):
        cohort = evidence['cohorts'][split]
        a, b = fig.axes[2*i:2*i+2]
        expected = [[p['local']['total_delta_v'], p['adp']['total_delta_v']] for p in cohort['pairs']]
        np.testing.assert_array_equal(a.collections[0].get_offsets(), expected)
        diffs = np.sort([p['adp']['graph_cost']-p['local']['graph_cost'] for p in cohort['pairs']])
        np.testing.assert_array_equal(b.collections[0].get_offsets()[:,1], diffs)
        assert len(b.collections[0].get_offsets()) == cohort['joint_success_n']
        assert b.patches[0].get_y() == cohort['bootstrap_95_ci'][0]
        np.testing.assert_allclose(b.patches[0].get_height(), np.diff(cohort['bootstrap_95_ci'])[0])
    plt.close(fig)


def test_safety_and_success_values_are_not_filtered_or_changed(evidence):
    figures.style()
    fig = figures.plot_safety(evidence)
    for index, split in enumerate(('test', 'ood')):
        for j, m in enumerate(figures.METHODS):
            record = evidence['success'][split][m]
            assert fig.axes[1].patches[index*4+j].get_width() == record['complete']/record['total']
        for ax, field in ((fig.axes[2], 'min_clearance'), (fig.axes[3], 'peak_input')):
            expected = [[p['local'][field], p['adp'][field]] for p in evidence['cohorts'][split]['pairs']]
            np.testing.assert_array_equal(ax.collections[index].get_offsets(), expected)
            points = np.asarray(expected)
            assert np.all((points[:,0] >= ax.get_xlim()[0]) & (points[:,0] <= ax.get_xlim()[1]))
            assert np.all((points[:,1] >= ax.get_ylim()[0]) & (points[:,1] <= ax.get_ylim()[1]))
    for bar, m in zip(fig.axes[0].patches, figures.METHODS[1:]):
        assert bar.get_height() == evidence['matched_effort']['methods'][m]['mean']
    plt.close(fig)


@pytest.mark.parametrize('builder', [figures.plot_performance, figures.plot_safety])
def test_final_size_text_and_tick_separation(evidence, builder):
    figures.style()
    fig = builder(evidence)
    fig.canvas.draw()
    assert len(fig.axes) == 4
    assert fig.get_figwidth()*72 == pytest.approx(239.10336239103364)
    renderer = fig.canvas.get_renderer()
    for ax in fig.axes:
        labels = [t for t in ax.get_xticklabels() if t.get_visible()]
        for left, right in zip(labels, labels[1:]):
            assert left.get_window_extent(renderer).x1 < right.get_window_extent(renderer).x0
        for text in [ax.xaxis.label, ax.yaxis.label, ax._left_title, *labels, *ax.get_yticklabels()]:
            if not text.get_text() or not text.get_visible():
                continue
            assert text.get_fontsize() == 9
            box = text.get_window_extent(renderer)
            assert box.x0 >= -1 and box.y0 >= -1
            assert box.x1 <= fig.bbox.width+1 and box.y1 <= fig.bbox.height+1
    plt.close(fig)


@pytest.mark.parametrize('builder', [figures.plot_performance, figures.plot_safety])
@pytest.mark.parametrize('index', range(4))
def test_independent_panels_keep_native_axes_and_readable_text(evidence, builder, index):
    figures.style()
    fig = figures.separate_panel(evidence, builder, index)
    fig.canvas.draw()
    assert len(fig.axes) == 1
    assert not fig.legends
    ax = fig.axes[0]
    renderer = fig.canvas.get_renderer()
    assert ax.get_title(loc='left') == ''
    assert ax.get_window_extent(renderer).width * 72 / fig.dpi == pytest.approx(77)
    labels = [t for t in ax.get_xticklabels() if t.get_visible()]
    for left, right in zip(labels, labels[1:]):
        assert left.get_window_extent(renderer).x1 < right.get_window_extent(renderer).x0
    for text in [ax.xaxis.label, ax.yaxis.label, *labels, *ax.get_yticklabels()]:
        if not text.get_text() or not text.get_visible():
            continue
        assert text.get_fontsize() == 9
        box = text.get_window_extent(renderer)
        assert box.x0 >= 0 and box.y0 >= 0
        assert box.x1 <= fig.bbox.width and box.y1 <= fig.bbox.height
    plt.close(fig)


def test_manuscript_uses_native_single_column_subfigures():
    text = (ROOT/'OrbInspectLatex/sections/required_target_study.tex').read_text()
    for name, label in (('adp_heldout_performance', 'fig:paired-performance'),
                        ('adp_ablation_safety', 'fig:paired-safety')):
        location = text.index(name+'_a.pdf')
        start = text.rfind(r'\begin{figure}', 0, location)
        assert start >= 0 and text.find(r'\end{figure}', start) > location
        block = text[start:text.find(r'\end{figure}', start)]
        assert block.count(r'\subfloat[') == 4
        for letter in 'abcd':
            assert name+'_'+letter+'.pdf' in block
            assert r'\label{'+label+'-'+letter+'}' in block
        assert name+'.pdf' not in block
        assert not re.search(r'\\subfloat\[\([a-d]\)', block)
    assert 'adp_ablation_safety_legend.pdf' in text
    reference = json.loads((ROOT/'OrbInspectLatex/data/confirmation/figure_reference.json').read_text())
    for record in reference['cohorts'].values():
        for value in [record['mean_graph_cost_difference'], *record['bootstrap_95_ci']]:
            assert f'{value:.2f}' in text


def test_exported_panels_are_vectors_with_consistent_dimensions_and_no_burned_labels():
    import fitz
    from PIL import Image
    import xml.etree.ElementTree as ET

    for folder in ('fig04_heldout_performance', 'fig05_ablation_safety'):
        root = ROOT/'OrbInspectLatex/figures'/folder
        manifest = json.loads((root/'single_column_manifest.json').read_text())
        assert manifest['generator_sha256'] == figures.sha(Path(figures.__file__))
        assert set('abcd') <= manifest['panels'].keys()
        for key, record in manifest['panels'].items():
            stem = root/record['stem']
            with fitz.open(stem.with_suffix('.pdf')) as doc:
                assert len(doc) == 1
                page = doc[0]
                assert page.rect.width == pytest.approx(record['width_pt'], abs=.001)
                assert page.rect.height == pytest.approx(record['height_pt'], abs=.001)
                assert not page.get_images()  # Native vector output, not a raster crop.
                assert not re.search(r'\([a-d]\)', page.get_text())
                assert page.get_fonts()
                assert all(doc.extract_font(font[0])[3] for font in page.get_fonts())
            svg = ET.parse(stem.with_suffix('.svg')).getroot()
            assert float(svg.attrib['width'].removesuffix('pt')) == pytest.approx(record['width_pt'], abs=.001)
            assert float(svg.attrib['height'].removesuffix('pt')) == pytest.approx(record['height_pt'], abs=.001)
            assert any(e.tag.endswith('}text') for e in svg.iter())
            with Image.open(stem.with_suffix('.png')) as image:
                assert abs(image.width-record['width_pt']/72*600) <= 1
                assert abs(image.height-record['height_pt']/72*600) <= 1
            assert record['axes'] == (0 if key == 'legend' else 1)
