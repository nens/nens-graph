import datetime
import matplotlib
import numpy

from django.http import HttpResponse

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.dates import date2num
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from matplotlib.ticker import ScalarFormatter

from nens_graph.common import MultilineAutoDateFormatter
from nens_graph.common import LessTicksAutoDateLocator
from nens_graph.common import NensGraph
from nens_graph.common import Converter
from nens_graph.common import DPI


class RainappGraph(NensGraph):
    """
    Class for matplotlib graphs, i.e. for popups, krw graphs

    - calculates correct size
    - horizontal axis = dates
    - vertical axis = user defined
    - outputs httpresponse for png
    """

    def __init__(self,
                 start_date, end_date,
                 width=None, height=None,
                 today=datetime.datetime.now(),
                 restrict_to_month=None):
        self.drawn = False
        self.restrict_to_month = restrict_to_month
        self.start_date = start_date
        self.end_date = end_date
        self.today = today
        self.converter = Converter()

        self.figure = Figure()
        if width is None or not width:
            width = 380.0
        if height is None or not height:
            height = 250.0
        self.width = float(width)
        self.height = float(height)
        self.figure.set_size_inches(
            (self.converter.inches_from_pixels(self.width),
             self.converter.inches_from_pixels(self.height)))
        self.figure.set_dpi(DPI)
        self.suptitle_obj = None
        # Figure color
        self.figure.set_facecolor('white')
        # Axes and legend location: full width is "1".
        self.axes = self.figure.add_axes([0, 0, 1, 1])
        self.axes.grid(True, linestyle='-', color='lightgrey', zorder=-999)
        self.axes.set_axisbelow(True)

        # Fixup_axes in init, so axes can be customised (for example set_ylim).
        self.fixup_axes()

        #deze kan je zelf zetten
        self.ax2 = None

    def add_today(self):
        # Show line for today.
        self.axes.axvline(self.today, color='orange', lw=1, ls='--')

    def set_ylim_margin(self, top=0.1, bottom=0.0):
        """Adjust y-margin of axes.

        The standard margin is sometimes zero. This method sets the margin
        based on already present data in the visible part of the plot, so
        call it after plotting and before http_png().

        Note that it is assumed here that the y-axis is not reversed.

        From matplotlib 1.0 on there is a set_ymargin method
        like this already."""

        lines = self.axes.lines
        arrays = [numpy.array(l.get_data()) for l in lines]

        # axhline and axvline give trouble - remove short lines from list
        big_arrays = [a for a in arrays if a.size > 4]
        if len(big_arrays) > 0:
            data = numpy.concatenate(big_arrays, axis=1)
            if len(data[0]) > 0:
                # Datatimes from database may have timezone information.
                # In that case, start_date and end_date cannot be naive.
                # Assume all datetimes do have the same timezone, so we
                # can do the comparison.
                start_date_tz =\
                    self.start_date.replace(tzinfo=data[0][0].tzinfo)
                end_date_tz =\
                    self.end_date.replace(tzinfo=data[0][0].tzinfo)
            index_in_daterange = ((data[0] < end_date_tz) &
                                  (data[0] > start_date_tz))
            if index_in_daterange.any():
                data_low = numpy.min(data[1, index_in_daterange])
                data_high = numpy.max(data[1, index_in_daterange])
                data_span = data_high - data_low
                view_low = data_low - data_span * bottom
                view_high = data_high + data_span * top
                self.axes.set_ylim(view_low, view_high)
        return None

    def suptitle(self, title):
        self.suptitle_obj = self.figure.suptitle(
            title,
            horizontalalignment='left')

    def set_xlabel(self, xlabel):
        """Store the label object for later use as well"""
        self.xlabel = self.axes.set_xlabel(xlabel)

    def set_ylabel(self, ylabel):
        """Store the label object for later use as well"""
        self.ylabel = self.axes.set_ylabel(ylabel, size='x-large')

    def fixup_axes(self, second=False):
        """Fix up the axes by limiting the amount of items."""

        axes_to_change = self.axes
        if second:
            if self.ax2 is None:
                return
            else:
                axes_to_change = self.ax2

        if not self.restrict_to_month:
            major_locator = LessTicksAutoDateLocator()
            axes_to_change.xaxis.set_major_locator(major_locator)

            major_formatter = MultilineAutoDateFormatter(
                major_locator, axes_to_change)
            axes_to_change.xaxis.set_major_formatter(major_formatter)

        if not second:
            # yaxis.set_major_locator(MaxNLocator(nbins=...) # Do this in the
            # on_draw, if necessary, based on size. pixel size or so.
            axes_to_change.yaxis.set_major_formatter(
                ScalarFormatter(useOffset=False))

    def legend(self, handles=None, labels=None):
        handles, labels = self.axes.get_legend_handles_labels()

        if handles and labels:
            nitems = len(handles)
            ncol = min(nitems, 3)
            # What comes next is an educated guess on the amount of
            # characters that can be used without collisions in the legend.
            ntrunc = int((self.width / ncol - 24) / 10)

            labels = [l[0:ntrunc] for l in labels]
            return self.axes.legend(handles,
                                    labels,
                                    bbox_to_anchor=(0., 0., 1., 0.),
                                    # bbox_transform=self.figure.transFigure,
                                    loc='right',
                                    ncol=ncol,
                                    # mode="expand",
                                    borderaxespad=0.)

        else:
            return None

         #legend.set_size('medium')
         # TODO: get rid of the border around the legend.

    def init_second_axes(self):
        """ init second axes """
        self.ax2 = self.axes.twinx()
        self.fixup_axes(second=True)

    def on_draw(self):
        """ Do last minute tweaks before actual rendering.

        This method is triggered by the draw_event, which is configured in the
        NensGraph class."""
        
        margin_in_pixels = 5
        xmargin = self.get_width_from_pixels(margin_in_pixels)
        ymargin = self.get_height_from_pixels(margin_in_pixels)

        suptitle_padding_in_pixels = 5
        xsuptitlepadding = self.get_width_from_pixels(suptitle_padding_in_pixels)
        ysuptitlepadding = self.get_height_from_pixels(suptitle_padding_in_pixels)

        ticklabelspace_in_pixels = 10  # This is unfortunately still an estimate
        xticklabelspace = self.get_width_from_pixels(ticklabelspace_in_pixels)
        yticklabelspace = self.get_height_from_pixels(ticklabelspace_in_pixels)

        # find out about the ytick_label heights
        yticklabelwidth = self.object_width(self.axes.get_yticklabels())
        ylabelwidth = self.object_width([self.ylabel])

        # find out about the legend height
        xticklabelheight = self.object_height(self.axes.get_xticklabels())
        if self.legend_obj:
            legendheight = self.object_height([self.legend_obj])
        else:
            legendheight = 0

        # Prepare dimensions of axis
        axes_x = xmargin + ylabelwidth + yticklabelwidth + yticklabelspace
        axes_y = ymargin + legendheight + xticklabelheight + xticklabelspace
        axes_width = 1 - axes_x - xmargin
        axes_height = 1 - axes_y - ymargin

        # adjust the layout accordingly
        if self.suptitle_obj:
            self.suptitle_obj.set_position(
                (axes_x + xsuptitlepadding,
                 1 - ymargin - ysuptitlepadding))
        self.axes.set_position((axes_x,
                                axes_y,
                                axes_width,
                                axes_height))

        # align the legend with the new axes layout
        if self.legend_obj:
            self.legend_obj.set_bbox_to_anchor(
                (axes_x,
                 ymargin,
                 axes_width,
                 legendheight),
                transform=self.figure.transFigure)


    def png_response(self):

        if not self.restrict_to_month:
            self.axes.set_xlim(date2num((self.start_date, self.end_date)))
            try:
                self.set_ylim_margin(top=0.1, bottom=0.0)
            except:
                pass

        major_locator = LessTicksAutoDateLocator()
        self.axes.xaxis.set_major_locator(major_locator)

        major_formatter = MultilineAutoDateFormatter(
            major_locator, self.axes)
        self.axes.xaxis.set_major_formatter(major_formatter)

        # Do final tweaks after data has been added to the axes
        ylim_old = self.axes.get_ylim()
        ylim_new = (ylim_old[0],
                    ylim_old[1] + 0.15 * (ylim_old[1] - ylim_old[0]))
        self.axes.set_ylim(ylim_new)

        self.axes.set_autoscaley_on(False)
        self.legend_obj = self.legend()

        return super(RainappGraph, self).png_response()

    def http_png(self):
        """Output plot to png. Also calculates size of plot and put 'now'
        line."""

        axes_left = self.left_label_width
        axes_bottom = (self.bottom_axis_location + self.x_label_height +
                       self.legend_on_bottom_height)
        axes_width = 1 - self.legend_width - self.left_label_width
        axes_height = (1 - 2 * self.bottom_axis_location -
                       self.x_label_height - self.legend_on_bottom_height)

        self.axes.set_position((axes_left, axes_bottom,
                                axes_width, axes_height))

        if self.ax2 is not None:
            self.ax2.set_position((axes_left, axes_bottom,
                                axes_width, axes_height))

