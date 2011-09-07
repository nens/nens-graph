from datetime import datetime
from datetime import timedelta
from numpy import array


from matplotlib.dates import date2num
from matplotlib.figure import Figure
from matplotlib.ticker import ScalarFormatter
from matplotlib.transforms import Bbox

from nens_graph.common import MultilineAutoDateFormatter
from nens_graph.common import LessTicksAutoDateLocator
from nens_graph.common import NensGraph
from nens_graph.common import Converter
from nens_graph.common import DPI


class RainappGraph(NensGraph):
    """Specialized graph class for the rainapp
    
    It is specifically intended for bar charts presently."""
    
    def __init__(self,
                 start_date,
                 end_date,
                 **kwargs):
        super(RainappGraph, self).__init__(**kwargs)
        self.start_date = start_date
        self.end_date = end_date
        self.restrict_to_month = kwargs.get('restrict_to_month')
        self.today = kwargs.get('today')

        self.suptitle_obj = None
        self.legend_obj = None
        self.axes = self.figure.add_axes([0, 0, 1, 1])
        self.axes.grid(True, linestyle='-', color='lightgrey', zorder=-999)
        self.axes.set_axisbelow(True)

        # Set the xlim and don't change anymore
        self.add_today()

    def add_today(self):
        # Show line for today.
        self.axes.axvline(self.today, color='orange', lw=1, ls='--')
   
    def get_bar_width(self, delta_t):
        """ Return width in data space for given timedelta."""
        date1 = datetime.now()
        date2 = date1 + delta_t
        width = date2num(date2) - date2num(date1)
        return width

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

    def legend(self, handles=None, labels=None):
        handles, labels = self.axes.get_legend_handles_labels()

        if handles and labels:
            nitems = len(handles)
            ncol = min(nitems, 3)
            # What comes next is an educated guess on the amount of
            # characters that can be used without collisions in the legend.
            ntrunc = int((self.width / ncol - 24) / 10)

            labels = [l[0:ntrunc] for l in labels]
            self.legend_obj = self.axes.legend(handles,
                              labels,
                              bbox_to_anchor=(0., 0., 1., 0.),
                              # bbox_transform=self.figure.transFigure,
                              loc='right',
                              ncol=ncol,
                              # mode="expand",
                              borderaxespad=0.)

    def on_draw(self):
        """ Do last minute tweaks before actual rendering.

        This method is triggered by the draw_event, which is configured in the
        NensGraph class."""

        margin_in_pixels = 5
        xmargin = self.get_width_from_pixels(margin_in_pixels)
        ymargin = self.get_height_from_pixels(margin_in_pixels)

        suptitle_padding_in_pixels = 5
        xsuptitlepadding = self.get_width_from_pixels(
            suptitle_padding_in_pixels)
        ysuptitlepadding = self.get_height_from_pixels(
            suptitle_padding_in_pixels)

        ticklabelspace_in_pixels = 10  # This is still an estimate
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
        
        # try:
        #     self.set_ylim_margin(top=0.1, bottom=0.0)
        # except:
        #     pass
        # self.set_ylim_margin(top=0.1, bottom=0.0)

        major_locator = LessTicksAutoDateLocator()
        self.axes.xaxis.set_major_locator(major_locator)

        major_formatter = MultilineAutoDateFormatter(
            major_locator, self.axes)
        self.axes.xaxis.set_major_formatter(major_formatter)

        # Do final tweaks after data has been added to the axes
        # ylim_old = self.axes.get_ylim()
        # ylim_new = (ylim_old[0],
        #             ylim_old[1] + 0.15 * (ylim_old[1] - ylim_old[0]))
        # self.axes.set_ylim(ylim_new)

        # self.legend()
        self.axes.set_xlim(date2num((self.start_date, self.end_date)))

        # find out about the data extents and set ylim accordingly
        if len(self.axes.patches) > 0:
            data_bbox = Bbox.union(
                [p.get_extents() for p in self.axes.patches])
            ymin, ymax = data_bbox.inverse_transformed(
                self.axes.transData).get_points()[:,1] * array([1, 1.1])
            ymax = max(1, ymax)
            ymin = -0.01 * ymax

            self.axes.set_ylim((ymin, ymax))

        return super(RainappGraph, self).png_response()
