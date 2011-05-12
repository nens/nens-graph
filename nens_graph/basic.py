from django.http import HttpResponse
from lizard_map.adapter import BOTTOM_LINE_HEIGHT
from lizard_map.adapter import LEFT_LABEL_WIDTH
from lizard_map.adapter import LEGEND_WIDTH
from lizard_map.adapter import _inches_from_pixels
from lizard_map.matplotlib_settings import FONT_SIZE
from lizard_map.matplotlib_settings import SCREEN_DPI
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

import csv
import logging
import os
import posixpath
import random
import urllib
import platform

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.static import serve
from haystack.forms import SearchForm
from haystack.query import SearchQuerySet
from lizard_map.models import Workspace
from lizard_map.workspace import WorkspaceManager
from pydap import client
from recaptcha.client import captcha

from deltaportaal.forms import ContactForm
from deltaportaal.forms import ProgramPermissionRequestForm
from deltaportaal.forms import SettingsForm
from deltaportaal.forms import UserForm
from deltaportaal.forms import UserProfileForm
from deltaportaal.graph import RiverGraph
from deltaportaal.models import GlossaryTerm
from deltaportaal.models import Measure
from deltaportaal.models import Program
from deltaportaal.models import ProgramFile
from deltaportaal.models import Strategy
from deltaportaal.models import relevant_parameters
from deltaportaal.programs import ProgramPermissionInfo
from deltaportaal.programs import user_overview
from deltaportaal.strategies import chosen_strategies
from deltaportaal.strategies import my_strategies
from deltaportaal.strategies import public_strategies

import datetime
import numpy

from dateutil.relativedelta import relativedelta
from dateutil.rrule import YEARLY, MONTHLY, DAILY, HOURLY, MINUTELY, SECONDLY
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.utils import simplejson as json
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.dates import DateFormatter
from matplotlib.dates import RRuleLocator
from matplotlib.dates import date2num
from matplotlib.dates import num2date
from matplotlib.dates import rrulewrapper
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from matplotlib.ticker import ScalarFormatter

from nens_graph.matplotlib_settings import FONT_SIZE
from nens_graph.matplotlib_settings import SCREEN_DPI

from nens_graph.common import LessTicksAutoDateLocator
from nens_graph.common import MultilineAutoDateFormatter

import logging
logger = logging.getLogger(__name__)


LEGEND_WIDTH = 200
LEFT_LABEL_WIDTH = 100
BOTTOM_LINE_HEIGHT = FONT_SIZE * 1.5
BOTTOM_LEGEND_HEIGHT = 100


_def inches_from_pixels(pixels):
    """Return size in inches for matplotlib's benefit"""
    return pixels / SCREEN_DPI


class Graph(object):
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
        self.restrict_to_month = restrict_to_month
        self.start_date = start_date
        self.end_date = end_date
        self.today = today

        self.figure = Figure()
        if width is None or not width:
            width = 380.0
        if height is None or not height:
            height = 250.0
        self.width = float(width)
        self.height = float(height)
        self.figure.set_size_inches((_inches_from_pixels(self.width),
                                     _inches_from_pixels(self.height)))
        self.figure.set_dpi(SCREEN_DPI)
        # Figure color
        self.figure.set_facecolor('white')
        # Axes and legend location: full width is "1".
        self.legend_width = 0.08
        # ^^^ No legend by default, but we *do* allow a little space to the
        # right of the graph to prevent the rightmost label from being cut off
        # (at least, in a reasonable percentage of the cases).
        self.left_label_width = LEFT_LABEL_WIDTH / self.width
        self.bottom_axis_location = BOTTOM_LINE_HEIGHT / self.height
        self.x_label_height = 0.08
        self.legend_on_bottom_height = 0.0
        self.axes = self.figure.add_subplot(111)
        self.axes.grid(True)

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
        self.figure.suptitle(title,
                             x=self.left_label_width,
                             horizontalalignment='left')

    def set_xlabel(self, xlabel):
        self.axes.set_xlabel(xlabel)
        self.x_label_height = BOTTOM_LINE_HEIGHT / self.height

    def fixup_axes(self, second=False):
        """Fix up the axes by limiting the amount of items."""

        axes_to_change = self.axes
        if second:
            if self.ax2 is None:
                return
            else:
                axes_to_change = self.ax2

#        available_width = self.width - LEFT_LABEL_WIDTH - LEGEND_WIDTH
#        approximate_characters = int(available_width / (FONT_SIZE / 2))
#        max_number_of_ticks = approximate_characters // 20
#        if max_number_of_ticks < 2:
#            max_number_of_ticks = 2
        if not self.restrict_to_month:
            major_locator = LessTicksAutoDateLocator()
            axes_to_change.xaxis.set_major_locator(major_locator)

            major_formatter = MultilineAutoDateFormatter(
                major_locator, axes_to_change)
            axes_to_change.xaxis.set_major_formatter(major_formatter)

        available_height = (self.height -
                            BOTTOM_LINE_HEIGHT -
                            self.x_label_height -
                            self.legend_on_bottom_height)
        approximate_lines = int(available_height / (FONT_SIZE * 1.5))
        max_number_of_ticks = approximate_lines
        if max_number_of_ticks < 2:
            max_number_of_ticks = 2
        locator = MaxNLocator(nbins=max_number_of_ticks - 1)
        if not second:
            axes_to_change.yaxis.set_major_locator(locator)
            axes_to_change.yaxis.set_major_formatter(
                ScalarFormatter(useOffset=False))

    def legend_space(self):
        """reserve space for legend (on the right side). even when
        there is no legend displayed"""
        self.legend_width = LEGEND_WIDTH / self.width

    def legend(self, handles=None, labels=None, ncol=1):
        """
        Displays legend. Default is right side, but if the width is
        too small, it will display under the graph.

        handles is list of matplotlib objects (e.g. matplotlib.lines.Line2D)
        labels is list of strings
        """
        # experimental update: do not reserve space for legend by
        # default, just place over graph. use legend_space to manually
        # add space

        if handles is None and labels is None:
            handles, labels = self.axes.get_legend_handles_labels()
        if handles and labels:
            # Determine 'small' or 'large'
            if self.width < 500:
                legend_loc = 4  # lower right
                # approximation of legend height
                self.legend_on_bottom_height = min(
                    (len(labels) / ncol + 2) * BOTTOM_LINE_HEIGHT /
                    self.height,
                    0.5)
            else:
                legend_loc = 1  # Upper right'

            return self.figure.legend(
                handles,
                labels,
                bbox_to_anchor=(1 - self.legend_width,
                                0,  # self.bottom_axis_location
                                self.legend_width,
                                # 1 = Upper right of above bbox. Use 0 for
                                # 'best'
                                1),
                loc=legend_loc,
                ncol=ncol,
                fancybox=True,
                shadow=True,)
         #legend.set_size('medium')
         # TODO: get rid of the border around the legend.

    def init_second_axes(self):
        """ init second axes """
        self.ax2 = self.axes.twinx()
        self.fixup_axes(second=True)

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

        # Set date range
        # Somehow, the range cannot be set in __init__
        if not self.restrict_to_month:
            self.axes.set_xlim(date2num((self.start_date, self.end_date)))
            try:
                self.set_ylim_margin(top=0.1, bottom=0.0)
            except:
                pass

        canvas = FigureCanvas(self.figure)
        response = HttpResponse(content_type='image/png')
        canvas.print_png(response)
        return response

from django.http import HttpResponse
from lizard_map.adapter import BOTTOM_LINE_HEIGHT
from lizard_map.adapter import LEFT_LABEL_WIDTH
from lizard_map.adapter import LEGEND_WIDTH
from lizard_map.adapter import _inches_from_pixels
from lizard_map.matplotlib_settings import FONT_SIZE
from lizard_map.matplotlib_settings import SCREEN_DPI
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

BOTTOM_LEGEND_HEIGHT = 100
