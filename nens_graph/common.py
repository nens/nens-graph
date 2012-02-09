# -*- coding: utf-8 -*-
from __future__ import division

import csv
import math
import iso8601

from matplotlib.transforms import Bbox
from matplotlib.figure import Figure
from matplotlib.dates import AutoDateFormatter
from matplotlib.dates import AutoDateLocator
from matplotlib.dates import DateFormatter
from matplotlib.dates import RRuleLocator
from matplotlib.dates import date2num
from matplotlib.dates import num2date
from matplotlib.dates import rrulewrapper


from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from datetime import datetime
from dateutil.rrule import YEARLY, MONTHLY, DAILY, HOURLY, MINUTELY, SECONDLY
from dateutil.relativedelta import relativedelta

import matplotlib
import logging
logger = logging.getLogger(__name__)

# Fonts and scales
FONTSIZE = 10
DPI = 72
RC_PARAMS = {
    'font.size': FONTSIZE,
    'legend.fontsize': FONTSIZE,
    'text.fontsize': FONTSIZE,
    'xtick.labelsize': FONTSIZE,
    'ytick.labelsize': FONTSIZE,
    }
matplotlib.rcParams.update(RC_PARAMS)


class NensGraph(object):
    """Base for all graphs in the nens_graph library. Provides methods for
    initialization and serving. The responseobject needs to be created in
    the calling application.

    Constructor arguments:
    - width (optional, default: 640)
    - height (optional, default: 480)
    - fontsize (optional, default: 10)
    - dpi (optional, default: 72)
    """

    def __init__(self, **kwargs):
        self.drawn = False
        self.responseobject = None
        self.width = kwargs.get('width', 640)
        self.height = kwargs.get('height', 480)
        self.fontsize = kwargs.get('fontsize', FONTSIZE)
        self.dpi = kwargs.get('dpi', DPI)

        inches_from_pixels = Converter(dpi=self.dpi).inches_from_pixels
        self.figure = Figure(figsize=(inches_from_pixels(self.width),
                                      inches_from_pixels(self.height)),
                             dpi=self.dpi,
                             facecolor='#ffffff')
        FigureCanvas(self.figure)
        self.renderer = self.figure.canvas.get_renderer()

    def object_width(self, objects):
        """Return width in figure coordinates of union of objects.
       The objects should support the get_window_extent()-method. Intended for
       use in the context of the on_draw method."""
        bboxes = []
        for o in objects:
            bbox = o.get_window_extent(renderer=self.renderer)
            # get_window_extent() gives pixels, we need figure coordinates:
            bboxi = bbox.inverse_transformed(self.figure.transFigure)
            bboxes.append(bboxi)
        bbox = Bbox.union(bboxes)
        return bbox.width

    def object_height(self, objects):
        """Return height in figure coordinates of union of objects.
       The objects should support the get_window_extent()-method. Intended for
       use in the context of the on_draw method."""
        bboxes = []
        for o in objects:
            bbox = o.get_window_extent()
            bbox = o.get_window_extent()
            # get_window_extent() gives pixels, we need figure coordinates:
            bboxi = bbox.inverse_transformed(self.figure.transFigure)
            bboxes.append(bboxi)
        bbox = Bbox.union(bboxes)
        return bbox.height

    def ticklabel_bbox(self, axis):
        """Return bbox in figure-coordinates of ticklabels."""
        ticklabel_extents = axis.get_ticklabel_extents(self.renderer)[0]
        bbox = ticklabel_extents.inverse_transformed(self.figure.transFigure)
        return bbox

    def on_draw_wrapper(self, event):
        """Avoid entering a loop, and avoid it here so that the inheriting
        classes don't have to bother."""
        if not self.drawn:
            self.on_draw()
            self.drawn = True
            self.figure.canvas.draw()
        return False

    def get_width_from_pixels(self, pixels):
        """Return the width in figure coordinates, given pixel width."""
        return self.figure.transFigure.inverted().transform([pixels, 0])[0]

    def get_height_from_pixels(self, pixels):
        """Return the height in figure coordinates, given pixel height."""
        return self.figure.transFigure.inverted().transform([0, pixels])[1]

    def on_draw(self):
        """Override this method for last minute tweaks to the layout. The
        above methods object width and object height only make sense in the
        context of this method."""
        pass

    def png_response(self, response=None):
        """
        Generate png response.

        if the class is used in Django:
        response = HttpResponse(content_type='image/png')
        """
        if response is None:
            response = self.responseobject
        if response is None:
            raise TypeError('Expected response object, not None.')

        # The renderer is used to audit the size of certain graph elements in
        # the functions object_width and object_height above.

        self.figure.canvas.mpl_connect('draw_event', self.on_draw_wrapper)
        self.figure.canvas.print_png(response)
        return response


def dates_values(timeseries, request_dates=None):
    """
    Return lists of dates, values, flag_dates and flag_values.

    Accepts single timeseries. Easy when using matplotlib.

    When request_dates is provided as list of dates, the result will
    only include dates that are in the list of request_dates.
    """
    dates = []
    values = []
    flag_dates = []
    flag_values = []
    timeseries_options = {}
    if request_dates is not None:
        timeseries_options['dates'] = request_dates
    for timestamp, (value, flag, comment) in timeseries.get_events(
        **timeseries_options):

        if value is not None:
            dates.append(timestamp)
            values.append(value)

            # Flags:
            # 0: Original/Reliable
            # 1: Corrected/Reliable
            # 2: Completed/Reliable
            # 3: Original/Doubtful
            # 4: Corrected/Doubtful
            # 5: Completed/Doubtful
            # 6: Missing/Unreliable
            # 7: Corrected/Unreliable
            # 8: Completed/Unreliable
            # 9: Missing value
            if flag > 2:
                flag_dates.append(timestamp)
                flag_values.append(flag)
    return dates, values, flag_dates, flag_values


class DateGridGraph(NensGraph):
    """
    Standard graph with a grid and dates on the x-axis.

    Inspired by lizard-map adapter.graph, but it is more generic.

    Note: margin_extra_xx is defined, it looks like you can just stack
    stuff. But don't do that - for each item the total-final-height of
    _every_ component is needed to calculate the exact location in
    pixels. So if you wanna stack something, you need to recalculate
    all coordinates of components.
    """
    MARGIN_TOP = 10
    MARGIN_BOTTOM = 25
    MARGIN_LEFT = 104
    MARGIN_RIGHT = 54

    def __init__(self, **kwargs):
        super(DateGridGraph, self).__init__(**kwargs)

        # # Calculate surrounding space. We want it to be a constant
        # # number of pixels. Safety check first.
        # if (self.width > self.MARGIN_LEFT + self.MARGIN_RIGHT and
        #     self.height > self.MARGIN_TOP + self.MARGIN_BOTTOM):

        #     self.figure.subplots_adjust(
        #         bottom=float(self.MARGIN_BOTTOM)/self.height,
        #         top=float(self.height-self.MARGIN_TOP)/self.height,
        #         left=float(self.MARGIN_LEFT)/self.width,
        #         right=float(self.width-self.MARGIN_RIGHT)/self.width)

        self.axes = self.figure.add_subplot(111)
        self.axes.grid(True)

        major_locator = LessTicksAutoDateLocator()
        self.axes.xaxis.set_major_locator(major_locator)

        self.margin_top_extra = 0
        self.margin_bottom_extra = 0
        self.margin_left_extra = 0
        self.margin_right_extra = 0

        major_formatter = MultilineAutoDateFormatter(
            major_locator, self.axes)
        self.axes.xaxis.set_major_formatter(major_formatter)

        # Keep a track of timeseries that went by, consist of 2-tuples
        # (label, timeseries)
        self.stored_timeseries = []

    def graph_width(self):
        """
        Return the current width in pixels.

        This width is considered '1' in the matplotlib coordinate system.
        """
        width = self.width - (
            self.MARGIN_LEFT + self.margin_left_extra +
            self.MARGIN_RIGHT + self.margin_right_extra)
        return max(width, 1)

    def graph_height(self):
        """
        Return the current height in pixels.

        This height is considered '1' in the matplotlib coordinate system.
        """
        height = self.height - (
            self.MARGIN_TOP + self.margin_top_extra +
            self.MARGIN_BOTTOM + self.margin_bottom_extra)
        return max(height, 1)

    def legend(self, handles=None, labels=None, legend_location=0):
        """
        Add a legend to a graph.

        'best' 	0
        'upper right' 	1
        'upper left' 	2
        'lower left' 	3
        'lower right' 	4
        'right' 	5
        'center left' 	6
        'center right' 	7
        'lower center' 	8
        'upper center' 	9
        'center' 	10
        """
        if not handles or not labels:
            handles, labels = self.axes.get_legend_handles_labels()

        if handles and labels:
            nitems = len(handles)
            if legend_location in [5, 6, 7]:
                ncol = 1
                legend_lines = nitems
            else:
                ncol = min(nitems, 2)
                # What comes next is an educated guess on the amount of
                # characters that can be used without collisions in the legend.
                ntrunc = int((self.width / ncol - 24) / 10)
                labels = [l[0:ntrunc] for l in labels]
                legend_lines = int(math.ceil(float(nitems) / ncol))

            if legend_location in [3, 4, 8]:
                # 11 is margin for legend, 10 is line height, 6 is extra
                # In pixels
                self.margin_bottom_extra += legend_lines * 10 + 11 + 6
                legend_y = -float(self.margin_bottom_extra -
                                  3 +  # 3 is for bottom space
                                  self.MARGIN_BOTTOM) / self.graph_height()
                # quite stupid, but the coordinate system changes when you
                # use set_position. So the graph is on the negative side.

                # x, y, width, height
                bbox_to_anchor = (0., legend_y, 1., 0.)
            elif legend_location in [7, ]:
                # In pixels
                self.margin_right_extra += 210
                legend_x = 1 + float(self.margin_right_extra
                                     ) / self.graph_width()
                bbox_to_anchor = (legend_x, 0., 0., 1.)
            else:
                # default
                bbox_to_anchor = (0., 0., 1., 1.)

            self.legend_obj = self.axes.legend(
                handles,
                labels,
                bbox_to_anchor=bbox_to_anchor,
                loc=legend_location,
                ncol=ncol,
                borderaxespad=0.,
                fancybox=True,
                shadow=True,)

    def line_from_single_ts(self, single_ts, graph_item,
                            default_color=None, flags=False):
        """
        Draw line(s) from a single timeseries.

        Color is a matplotlib color, i.e. 'blue', 'black'

        Graph_item can contain an attribute 'layout'.
        """
        dates, values, flag_dates, flag_values = dates_values(single_ts)
        if not values:
            return

        layout = graph_item.layout_dict()

        label = layout.get('label', '%s - %s (%s)' % (
                single_ts.location_id, single_ts.parameter_id,
                single_ts.units))
        self.stored_timeseries.append((label, single_ts))
        style = {
            'label': label,
            'color': layout.get('color', default_color),
            'lw': layout.get('line-width', 2),
            'ls': layout.get('line-style', '-'),
            }

        # Line
        self.axes.plot(dates, values, **style)
        # Flags: style is not customizable.
        if flags:
            self.axes.plot(flag_dates, flag_values, "o-", color='red',
                           label=label + ' flags')

    def horizontal_line(self, value, layout, default_color=None):
        """
        Draw horizontal line.
        """
        style = {
            'ls': layout.get('line-style', '-'),
            'lw': int(layout.get('line-width', 2)),
            'color': layout.get('color', default_color),
            }
        if 'label' in layout:
            style['label'] = layout['label']
        self.axes.axhline(float(value), **style)

    def vertical_line(self, value, layout, default_color=None):
        """
        Draw vertical line.
        """
        style = {
            'ls': layout.get('line-style', '-'),
            'lw': int(layout.get('line-width', 2)),
            'color': layout.get('color', default_color),
            }
        if 'label' in layout:
            style['label'] = layout['label']
        try:
            dt = iso8601.parse_date(value)
        except iso8601.ParseError:
            dt = datetime.datetime.now()
        self.axes.axvline(dt, **style)

    def bar_from_single_ts(self, single_ts, graph_item, bar_width,
                           default_color=None, bottom_ts=None):
        """
        Draw bars.

        Graph_item can contain an attribute 'layout'.

        Bottom_ts and single_ts MUST have the same timestamps. This
        can be accomplished by: single_ts = single_ts + bottom_ts * 0
        bottom_ts = bottom_ts + single_ts * 0

        bar_width in days
        """

        dates, values, flag_dates, flag_values = dates_values(single_ts)

        bottom = None
        if bottom_ts:
            bottom = dates_values(bottom_ts, request_dates=dates)

        if not values:
            return

        layout = graph_item.layout_dict()

        label = layout.get('label', '%s - %s (%s)' % (
            single_ts.location_id, single_ts.parameter_id, single_ts.units))
        self.stored_timeseries.append((label, single_ts))

        style = {'color': layout.get('color', default_color),
                 'edgecolor': layout.get('color-outside', 'grey'),
                 'label': label,
                 'width': bar_width}
        if bottom:
            style['bottom'] = bottom[1]  # 'values' of bottom
        self.axes.bar(dates, values, **style)

    def set_margins(self):
        """
        Set the graph margins.

        Using MARGIN settings and margin_legend_bottom (in
        pixels). Call after adding legend and other stuff, just before
        png_response.
        """
        # Calculate surrounding space. We want it to be a constant
        # number of pixels. Safety check first, else just "do something".
        if (self.width > self.MARGIN_LEFT + self.margin_left_extra +
            self.MARGIN_RIGHT + self.margin_right_extra and
            self.height > self.MARGIN_TOP + self.margin_top_extra +
            self.MARGIN_BOTTOM + self.margin_bottom_extra):

            # x, y, width, height.. all from 0..1
            axes_x = float(self.MARGIN_LEFT +
                           self.margin_left_extra) / self.width
            axes_y = float(self.MARGIN_BOTTOM +
                           self.margin_bottom_extra) / self.height
            axes_width = float(self.width -
                               (self.MARGIN_LEFT +
                                self.margin_left_extra +
                                self.MARGIN_RIGHT +
                                self.margin_right_extra)) / self.width
            axes_height = float(self.height -
                                (self.MARGIN_TOP +
                                 self.margin_top_extra +
                                 self.MARGIN_BOTTOM +
                                 self.margin_bottom_extra)) / self.height
            self.axes.set_position((axes_x, axes_y, axes_width, axes_height))

    def timeseries_csv(self, response=None):
        """
        Writes csv in provided (django) response.

        If response is omitted, output will be on std out (for debugging).
        """
        if response is None:
            for label, ts in self.stored_timeseries:
                print label
                print ts.get_events()
            return
        writer = csv.writer(response)
        for label, ts in self.stored_timeseries:
            writer.writerow([label])
            writer.writerow(['datetime', 'value', 'flag', 'comment'])
            for dt, (value, flag, comment) in ts.get_events():
                writer.writerow([dt, value, flag, comment])


class Converter(object):
    """Conversion methods for graphs."""
    def __init__(self, dpi=72):
        self.dpi = dpi

    def inches_from_pixels(self, pixels):
        """Return size in inches for matplotlib's benefit"""
        return float(pixels) / self.dpi


class LessTicksAutoDateLocator(AutoDateLocator):
    """Similar to matplotlib.date.AutoDateLocator, but with less ticks."""

    def __init__(self, tz=None, numticks=7):
        AutoDateLocator.__init__(self, tz)
        self.numticks = numticks

    def get_locator(self, dmin, dmax):
        'Pick the best locator based on a distance.'

        delta = relativedelta(dmax, dmin)

        numYears = (delta.years * 1.0)
        numMonths = (numYears * 12.0) + delta.months
        numDays = (numMonths * 31.0) + delta.days
        numHours = (numDays * 24.0) + delta.hours
        numMinutes = (numHours * 60.0) + delta.minutes
        numSeconds = (numMinutes * 60.0) + delta.seconds

        # numticks = 5
        # Difference to original AutoDateLocator: less ticks
        numticks = self.numticks

        # self._freq = YEARLY
        interval = 1
        bymonth = 1
        bymonthday = 1
        byhour = 0
        byminute = 0
        bysecond = 0
        if (numYears >= numticks):
            self._freq = YEARLY
            interval = int(numYears // numticks)
        elif (numMonths >= numticks):
            self._freq = MONTHLY
            bymonth = range(1, 13)
            interval = int(numMonths // numticks)
        elif (numDays >= numticks):
            self._freq = DAILY
            bymonth = None
            bymonthday = range(1, 32)
            interval = int(numDays // numticks)
        elif (numHours >= numticks):
            self._freq = HOURLY
            bymonth = None
            bymonthday = None
            byhour = range(0, 24)      # show every hour
            interval = int(numHours // numticks)
        elif (numMinutes >= numticks):
            self._freq = MINUTELY
            bymonth = None
            bymonthday = None
            byhour = None
            byminute = range(0, 60)
            interval = int(numMinutes // numticks)
            # end if
        elif (numSeconds >= numticks):
            self._freq = SECONDLY
            bymonth = None
            bymonthday = None
            byhour = None
            byminute = None
            bysecond = range(0, 60)
            interval = int(numSeconds // numticks)
            # end if
        else:
            # do what?
            #   microseconds as floats, but floats from what reference point?
            pass

        rrule = rrulewrapper(self._freq, interval=interval,
                             dtstart=dmin, until=dmax,
                             bymonth=bymonth, bymonthday=bymonthday,
                             byhour=byhour, byminute=byminute,
                             bysecond=bysecond)

        locator = RRuleLocator(rrule, self.tz)
        locator.set_axis(self.axis)

        locator.set_view_interval(*self.axis.get_view_interval())
        locator.set_data_interval(*self.axis.get_data_interval())
        return locator


class MultilineAutoDateFormatter(AutoDateFormatter):
    """Multiline version of AutoDateFormatter.

    This class needs the axes to be able to initialize. When called, the
    ticks need to be known as well. For some scales, instead of showing a
    predetermined date label at any tick, the labels are chosen dependent of
    the tick position. Note that some labels are multiline, so make sure
    there is space for them in your figure."""

    def __init__(self, locator, axes, tz=None):
        self._locator = locator
        self._formatter = DateFormatter("%b %d %Y %H:%M:%S %Z", tz)
        self._tz = tz
        self.axes = axes
        self.tickinfo = None

    def __call__(self, x, pos=0):

        scale = float(self._locator._get_unit())
        if not self.tickinfo:
            self.tickinfo = self.Tickinfo(self.axes.get_xticks())

        if (scale == 365.0):
            self._formatter = DateFormatter("%Y", self._tz)
        elif (scale == 30.0):
            if self.tickinfo.show_year(x):
                self._formatter = DateFormatter("%b\n%Y", self._tz)
            else:
                self._formatter = DateFormatter("%b", self._tz)
        elif ((scale == 1.0) or (scale == 7.0)):
            if self.tickinfo.show_month(x):
                self._formatter = DateFormatter("%d\n%b %Y", self._tz)
            else:
                self._formatter = DateFormatter("%d", self._tz)
        elif (scale == (1.0 / 24.0)):
            if x == self.tickinfo.max:
                # don't show
                self._formatter = DateFormatter("%H", self._tz)
            elif self.tickinfo.show_day(x):
                self._formatter = DateFormatter("%H\n%d %b %Y", self._tz)
            else:
                self._formatter = DateFormatter("%H", self._tz)
        elif (scale == (1.0 / (24 * 60))):
            self._formatter = DateFormatter("%H:%M:%S %Z", self._tz)
        elif (scale == (1.0 / (24 * 3600))):
            self._formatter = DateFormatter("%H:%M:%S %Z", self._tz)
        else:
            self._formatter = DateFormatter("%b %d %Y %H:%M:%S %Z", self._tz)

        return self._formatter(x, pos)

    class Tickinfo(object):
        """ Class with tick information.

        The methods are used to determine what kind of label to put at a
        particular tick."""

        def __init__(self, ticks):
            self.ticks = ticks
            self.min = ticks[0]
            self.max = ticks[-1]
            self.step = ticks[1] - ticks[0]
            self.span = ticks[-1] - ticks[0]
            self.mid = ticks[int((len(ticks) - 1) / 2)]

        def show_day(self, tick):
            """ Return true or false to show day at this tick."""

            # If there is only one day in the ticks, show it at the center
            if (num2date(self.min).day == num2date(self.max).day):
                if tick == self.mid:
                    return True
                else:
                    return False

            # If there are more days in the ticks, show a label for that
            # tick that is closest to the center of their day.
            else:
                middle_of_day = self.middle_of_day(tick)
                if (abs(tick - middle_of_day) < self.step / 2 or
                    (middle_of_day < self.min and tick == self.min) or
                    (middle_of_day > self.max) and tick == self.max):
                    return True
                else:
                    return False

        def show_month(self, tick):
            """ Return true or false to show month at this tick."""

            # If there is only one month in the ticks, show it at the center
            if (num2date(self.min).month == num2date(self.max).month):
                if tick == self.mid:
                    return True
                else:
                    return False

            # If there are more months in the ticks, show a label for that
            # tick that is closest to the center of their month.
            else:
                middle_of_month = self.middle_of_month(tick)
                if (abs(tick - middle_of_month) < self.step / 2 or
                    (middle_of_month < self.min and tick == self.min) or
                    (middle_of_month > self.max) and tick == self.max):
                    return True
                else:
                    return False

        def show_year(self, tick):
            """ Return true or false to show year at this tick."""

            # If there is only one year in the ticks, show it at the center
            if (num2date(self.min).year == num2date(self.max).year):
                if tick == self.mid:
                    return True
                else:
                    return False

            # If there are more years in the ticks, show a label for that
            # tick that is closest to the center of their year.
            else:
                middle_of_year = self.middle_of_year(tick)
                if (abs(tick - middle_of_year) < self.step / 2 or
                    (middle_of_year < self.min and tick == self.min) or
                    (middle_of_year > self.max) and tick == self.max):
                    return True
                else:
                    return False

        def middle_of_day(self, tick):
            """ Return the middle of the day as matplotlib number. """
            dt = num2date(tick)
            middle_of_day = datetime(dt.year, dt.month, dt.day, 12)
            return date2num(middle_of_day)

        def middle_of_month(self, tick):
            """ Return the middle of the month as matplotlib number. """
            dt = num2date(tick)
            middle_of_month = datetime(dt.year, dt.month, 16)
            return date2num(middle_of_month)

        def middle_of_year(self, tick):
            """ Return the middle of the year as matplotlib number. """
            dt = num2date(tick)
            middle_of_year = datetime(dt.year, 7, 1)
            return date2num(middle_of_year)
