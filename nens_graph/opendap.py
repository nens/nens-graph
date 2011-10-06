from __future__ import division
from datetime import datetime
from logging import getLogger
from nens_graph.common import NensGraph
from nens_graph.common import MultilineAutoDateFormatter
from nens_graph.common import LessTicksAutoDateLocator

from matplotlib import cm
from matplotlib.dates import date2num

logger = getLogger(__name__)


class OpendapGraph(NensGraph):
    """Class for matplotlib river graphs."""

    def __init__(self,
                 start_km=None,
                 end_km=None,
                 today=datetime.now(),
                 *args,
                 **kwargs):

        super(OpendapGraph, self).__init__(*args, **kwargs)

        # self.figure.set_facecolor('#bbbbbb')
        self.start_date = kwargs.get('start_date', None)
        self.end_date = kwargs.get('end_date', None)
        self.restrict_to_month = kwargs.get('restrict_to_month', None)
        self.today = today
        self.drawn = False

        # Layout of the axes in the figure
        self.axes = self.figure.add_axes([0, 0, 1, 1])
        self.axes.grid(True, linestyle='-', color='lightgrey')
        self.suptitle_obj = None
        self.legend_obj = None
        self.ylabel = None
        self.xlabel = None

        # bar style options and initializations
        self.legend_handles = []
        self.legend_labels = []
        self.polysize = 70
        self.circlesize = 40
        self.legend_markersize = 7
        self.legend_markeredgewidth = 1.2
        self.colormap = cm.cool
        self.patch_zorder = 10

    def suptitle(self, title):
        self.suptitle_obj = self.figure.suptitle(title,
                             horizontalalignment='left',
                             verticalalignment='top')

    def set_xlabel(self, xlabel):
        self.xlabel = self.axes.set_xlabel(xlabel,
                                           size='large',
                                           horizontalalignment='right',
                                           verticalalignment='center')

    def set_ylabel(self, ylabel):
        self.ylabel = self.axes.set_ylabel(ylabel,
                                           size='large',
                                           horizontalalignment='right',
                                           verticalalignment='center')

    def add_today(self):
        # Show line for today.
        self.axes.axvline(self.today, color='orange', lw=1, ls='--')

    def legend(self, handles=None, labels=None):
        handles, labels = self.axes.get_legend_handles_labels()

        if handles and labels:
            nitems = len(handles)
            ncol = int((nitems - 1) / 3) + 1
            # What comes next is an educated guess on the amount of
            # characters that can be used without collisions in the legend.
            ntrunc = int((self.width / ncol - 24) / 8)

            labels = [l[0:ntrunc] for l in labels]
            return self.axes.legend(handles,
                                    labels,
                                    bbox_to_anchor=(0., 0., 1., 0.),
                                    # bbox_transform=self.figure.transFigure,
                                    loc=3,
                                    ncol=ncol,
                                    mode="expand",
                                    borderaxespad=0.,)

        else:
            return None

    def png_response(self):

        if not self.restrict_to_month:
            self.axes.set_xlim(date2num((self.start_date, self.end_date)))

        # Do final tweaks after data has been added to the axes
        ylim_old = self.axes.get_ylim()
        ylim_new = (ylim_old[0],
                    ylim_old[1] + 0.15 * (ylim_old[1] - ylim_old[0]))
        self.axes.set_ylim(ylim_new)

        self.axes.set_autoscaley_on(False)
        self.legend_obj = self.legend()

        return super(OpendapGraph, self).png_response()

    def on_draw(self):
        """ Do last minute tweaks before actual rendering.

        This method is triggered by the draw_event, which is configured in the
        NensGraph class."""

        if not self.restrict_to_month:
            major_locator = LessTicksAutoDateLocator()
            major_formatter = MultilineAutoDateFormatter(
                major_locator, self.axes)
            self.axes.xaxis.set_major_locator(major_locator)
            self.axes.xaxis.set_major_formatter(major_formatter)

        margin_in_pixels = 5
        xmargin = self.get_width_from_pixels(margin_in_pixels)
        ymargin = self.get_height_from_pixels(margin_in_pixels)

        suptitle_padding_in_pixels = 5
        xsuptitlepadding = self.get_width_from_pixels(
            suptitle_padding_in_pixels)
        ysuptitlepadding = self.get_height_from_pixels(
            suptitle_padding_in_pixels)

        xextraspace_in_pixels = 10  # This is still an estimate
        yextraspace_in_pixels = 10  # This is still an estimate
        xextraspace = self.get_height_from_pixels(xextraspace_in_pixels)
        yextraspace = self.get_width_from_pixels(yextraspace_in_pixels)

        # find out about the (tick)label size
        yticklabelwidth = self.ticklabel_bbox(self.axes.yaxis).width
        xticklabelheight = self.ticklabel_bbox(self.axes.xaxis).height

        if self.ylabel:
            ylabelwidth = self.object_width([self.ylabel])
        else:
            ylabelwidth = 0
        if self.xlabel:
            xlabelheight = self.object_height([self.xlabel])
        else:
            xlabelheight = 0

        # find out about the legend height
        if self.legend_obj:
            legendheight = self.object_height([self.legend_obj])
        else:
            legendheight = 0

        # Prepare dimensions of axis
        axes_x = xmargin + ylabelwidth + yticklabelwidth + yextraspace
        axes_y = (ymargin + xlabelheight + xticklabelheight + xextraspace +
                  legendheight)

        logger.debug(xlabelheight)
        axes_width = 1 - axes_x - xmargin
        axes_height = 1 - axes_y - ymargin

        # adjust the layout accordingly
        logger.debug(self.suptitle_obj)
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
