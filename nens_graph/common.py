from __future__ import division

from matplotlib.figure import Figure
from matplotlib.dates import AutoDateFormatter
from matplotlib.dates import AutoDateLocator

import matplotlib

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from django.http import HttpResponse


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
    initialization and serving."""

    def __init__(self, **kwargs):
        self.width = kwargs.get('width', 640)
        self.height = kwargs.get('height', 480)
        self.fontsize = kwargs.get('fontsize', FONTSIZE)
        self.dpi = kwargs.get('dpi', DPI)

        inches_from_pixels = Converter(dpi=self.dpi).inches_from_pixels
        self.figure = Figure(figsize=(inches_from_pixels(self.width),
                                      inches_from_pixels(self.height)),
                             dpi=self.dpi,
                             facecolor='#ffffff')

    def http_png(self):
        canvas = FigureCanvas(self.figure)
        response = HttpResponse(content_type='image/png')
        self.figure.canvas.print_png(response)
        return response


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
            middle_of_day = datetime.datetime(dt.year, dt.month, dt.day, 12)
            return date2num(middle_of_day)

        def middle_of_month(self, tick):
            """ Return the middle of the month as matplotlib number. """
            dt = num2date(tick)
            middle_of_month = datetime.datetime(dt.year, dt.month, 16)
            return date2num(middle_of_month)

        def middle_of_year(self, tick):
            """ Return the middle of the year as matplotlib number. """
            dt = num2date(tick)
            middle_of_year = datetime.datetime(dt.year, 7, 1)
            return date2num(middle_of_year)


class AutoLabelWidthAdjuster(object):
    """A tool for the automatic adjustment of the axes extents to accomodate
    the varying size of the ticklabels."""
    def __init__(self, figure):
        pass

    def adjust_left_axis(event):
        pass
#       bboxes = []
#       for label in labels:
#           bbox = label.get_window_extent()
#           # the figure transform goes from relative coords->pixels and we
#           # want the inverse of that
#           bboxi = bbox.inverse_transformed(fig.transFigure)
#           bboxes.append(bboxi)

#       # this is the bbox that bounds all the bboxes, again in relative
#       # figure coords
#       bbox = mtransforms.Bbox.union(bboxes)
#       if fig.subplotpars.left < bbox.width:
#           # we need to move it over
#           fig.subplots_adjust(left=1.1*bbox.width) # pad a little
#           fig.canvas.draw()
#       return False

#    fig.canvas.mpl_connect('draw_event', on_draw)

#    plt.show()
#
