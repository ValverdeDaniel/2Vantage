"""A recorded `bars` frame as a native, editable PowerPoint chart (plan.md §9.6; J127, J128, J141). Ported from old
Vantage 891f1b3 `pipeline/proposal_deck._bars`: clustered columns, a figure over each column, no gridlines and no
value axis, the legend under the plot only when there are two or more series, each series and column in the colour the
PDF drew. The story records a chart only with two or more rows (J128); a None value is no column.
"""

from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.util import Pt

from .units import FAMILY, emu, rgb

MONEY = '$#,##0'
CHANGE = '+0.0"%";-0.0"%"'


def bars(slide, it, _pictures=None):
    data = CategoryChartData()
    data.categories = it['categories']
    for entry in it['series']:
        data.add_series(entry['name'], entry['values'])
    frame = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, emu(it['x']), emu(it['y']), emu(it['w']), emu(it['h']), data
    )
    chart = frame.chart
    chart.has_legend = len(it['series']) > 1
    if chart.has_legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
    chart.font.size = Pt(11)
    chart.font.name = FAMILY
    number_format = MONEY if it['money'] else CHANGE
    chart.value_axis.tick_labels.number_format = number_format
    chart.value_axis.tick_labels.number_format_is_linked = False
    chart.value_axis.has_major_gridlines = False
    chart.value_axis.visible = False
    plot = chart.plots[0]
    plot.gap_width = 60
    plot.overlap = 0
    plot.has_data_labels = True
    plot.data_labels.number_format = number_format
    plot.data_labels.number_format_is_linked = False
    plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    for series, entry in zip(plot.series, it['series'], strict=True):
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = rgb(entry['color'])
        for number, colour in enumerate(entry.get('colors') or []):
            if colour:
                point = series.points[number].format.fill
                point.solid()
                point.fore_color.rgb = rgb(colour)
    return frame
