# SPDX-License-Identifier: AGPL-3.0-only
#
# Part of "usage". Free software licensed under the GNU Affero General Public
# License v3.0 only; see the LICENSE file for full terms and the warranty disclaimer.

"""What a masked share must not carry.

The report offers "mask project names" before an HTML, CSV or PNG download. The
masking runs in the browser, but what it *can* reach is decided here, when the
page is rendered: a name inlined into the report script, or parked in an
attribute, leaves with the file no matter what the JavaScript does to the
visible text.
"""

from __future__ import annotations

from typing import Any

from tests.test_html_report_snapshot import _full_report_data
from ui import html_report
from ui.report_scripts import REPORT_JS_TEMPLATE

_SECRET_PROJECTS = ("usage", "client<portal>")


def _rendered(language: str = "en") -> str:
    return html_report.generate_html(_full_report_data(), language=language)


def test_the_unmasked_csv_sits_in_a_node_the_export_can_drop() -> None:
    """It used to be a const inside the report script, where nothing could remove it."""
    html = _rendered()

    assert '<script type="application/json" data-report-csv>' in html
    assert '<script type="application/json" data-report-csv-masked>' in html
    assert "const csvData = readJsonNode('[data-report-csv]', maskedCsvData);" in html
    # The literal payload must not be back inside the script body.
    assert 'const csvData = "type,name' not in html


def test_the_masked_csv_payload_carries_no_real_project_name() -> None:
    masked = html_report._build_csv_data(_full_report_data(), "en", mask_projects=True)

    assert "project,Project 1," in masked
    for project in _SECRET_PROJECTS:
        assert project not in masked


def test_masking_removes_the_unmasked_payload_and_falls_back() -> None:
    removal = "document.querySelectorAll('[data-report-csv]').forEach((el) => {"
    fallback = "const maskedCsvData = readJsonNode('[data-report-csv-masked]', '');"

    assert removal in REPORT_JS_TEMPLATE
    assert fallback in REPORT_JS_TEMPLATE


def test_the_donut_legend_can_be_masked_and_names_no_project_in_an_attribute() -> None:
    """The legend spans are .lg-name, which the .name selectors never covered."""
    html = _rendered()
    legend_start = html.index('<ul class="donut-legend">')
    legend = html[legend_start : html.index("</ul>", legend_start)]

    assert 'data-mask-index="1"' in legend
    assert 'data-mask-index="2"' in legend
    # The rank travels, the name does not.
    for project in _SECRET_PROJECTS:
        assert f'data-mask-index="{project}"' not in legend
        assert f'data-project-name="{project}"' not in html


def test_an_insight_sentence_marks_the_project_name_rather_than_the_sentence() -> None:
    html = _rendered()

    assert '<span class="masked-name" data-mask-index="1">usage</span>' in html
    # Masking the whole sentence would throw away the number beside the name.
    assert "70.2%" in html


def test_project_ranks_follow_the_table_order() -> None:
    data: dict[str, Any] = {
        "by_project": [
            {"project": "alpha"},
            {"project": "beta"},
            {"project": "gamma"},
        ]
    }

    assert html_report._project_ranks(data) == {"alpha": 1, "beta": 2, "gamma": 3}


def test_project_ranks_stop_where_the_legend_does() -> None:
    """The donut shows six projects and folds the rest into one bucket.

    A rank past the sixth would mask to a label no legend entry carries.
    """
    data: dict[str, Any] = {"by_project": [{"project": f"p{index}"} for index in range(9)]}

    ranks = html_report._project_ranks(data)

    assert len(ranks) == 6
    assert ranks["p5"] == 6
    assert "p6" not in ranks


def test_an_unranked_project_still_gets_masked_in_an_insight() -> None:
    """Insights can name a project the table does not rank; it must not leak."""
    component = {"key": "spike", "type": "spike", "project": "not-in-table"}

    kwargs = html_report._insight_kwargs(component, {"other": 1})

    assert kwargs["project"] == '<span class="masked-name" data-mask>not-in-table</span>'
