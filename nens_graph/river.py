from math import pi
from numpy import arange
from numpy import array
from numpy import concatenate
from logging import getLogger
from django.http import HttpResponse
from nens_graph.common import NensGraph

from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib import cm
from matplotlib.collections import RegularPolyCollection
from matplotlib.collections import CircleCollection
from matplotlib.patches import RegularPolygon
from matplotlib.patches import Circle
from matplotlib.lines import Line2D
from matplotlib.text import Text

logger = getLogger(__name__)

class RiverGraph(NensGraph):
    """Class for matplotlib river graphs
    
    Copy/pasted from lizard_map/adapter.py and adapted to our needs.

    Basic test:

      >>> graph = RiverGraph()
      >>> graph = RiverGraph(10, 20, 400, 300)
      >>> graph.suptitle('test')
      >>> graph.set_xlabel('test')
      >>> graph.fixup_axes()
      >>> graph.legend_space()
      >>> graph.legend()
      >>> output = graph.http_png()

    """

    def __init__(self,
                 start_km=None,
                 end_km=None,
                 *args,
                 **kwargs):

        super(RiverGraph, self).__init__(*args, **kwargs)
        
        #self.figure.set_facecolor('#bbbbbb')
        self.start_km = start_km
        self.end_km = end_km

        # Layout of the axes in the figure
        axes_left = 0.1
        axes_width = 0.87
        self.axes = self.figure.add_axes([axes_left,
                                          0.31,
                                          axes_width,
                                          0.49],
                                         ylabel='MHW overschrijding [m]')
        self.axes.grid(True, linestyle='-',color='lightgrey')
        self.axes.invert_xaxis()
        self.bar_axes = self.figure.add_axes([axes_left,
                                              0.10,
                                              axes_width,
                                              0.20],
                                             xlabel='Rivier Kilometer')
        self.bar_axes.grid(True, linestyle='-',color='lightgrey')
        self.bar_axes.set_ylim((-0.05,1.1))
        self.bar_axes.get_yaxis().set_ticks([0.1,0.3,0.5,0.7,0.9])
        self.bar_axes.get_yaxis().set_ticklabels(['knelpt','Retent','Dijk','Onttr','Overig'])
        
        # bar style options and initializations
        self.legend_handles = []
        self.legend_labels = []
        self.polysize = 70
        self.circlesize = 40
        self.legend_markersize = 7
        self.legend_markeredgewidth = 1.2
        self.colormap = cm.cool
        self.patch_zorder = 10

        # Add fake patches at fake positions
        from random import choice
        from random import seed
        seed(0)
        xlim = self.axes.get_xlim()
        step = (max(xlim) - min(xlim)) / 40
        kms = arange(xlim[1] + step, xlim[0] - step, step)
        iters = 25

    def http_png(self):

        # Do final tweaks after data has been added to the axes
        ylim_old = self.axes.get_ylim()
        ylim_new = (ylim_old[0],
                    ylim_old[1] + 0.15 * (ylim_old[1] - ylim_old[0]))
        self.axes.set_ylim(ylim_new)
        self.bar_axes.set_xlim(self.axes.get_xlim())
        for l in self.axes.get_xaxis().get_majorticklabels():
            l.set_visible(False)
        for l in self.bar_axes.get_yaxis().get_majorticklabels():
            l.set_horizontalalignment('left')
            l.set_position((-.08,0))

        self.axes.set_autoscaley_on(False)
        self.axes.axhline(0,
                          color='#030303',
                          linestyle=':',
                          linewidth=3,
                          label='Nullijn')

        # Add fake patches at fake positions
        from random import choice
        from random import seed
        seed(0)
        xlim = self.axes.get_xlim()
        step = (max(xlim) - min(xlim)) / 40
        kms = arange(xlim[1] + step, xlim[0] - step, step)
        iters = 25
    
        self.add_diamonds([choice(kms) for i in range(iters)])
        self.add_uptriangles([choice(kms) for i in range(iters)])
        self.add_squares([choice(kms) for i in range(iters)])
        self.add_downtriangles([choice(kms) for i in range(iters)])
        self.add_circles([choice(kms) for i in range(iters)])

        # Add some test place_names
        self.add_text((xlim[1] + (xlim[0] - xlim[1]) * 0.2,
                       xlim[1] + (xlim[0] - xlim[1]) * 0.5,
                       xlim[1] + (xlim[0] - xlim[1]) * 0.7),
                      ('Plaats C',
                       'Plaats B',
                       'Plaats A'))
        
        self.legend()
            
        return super(RiverGraph, self).http_png()

    def add_diamonds(self, kms):
        """Add diamonds to bar_axes at specified kms.
        
        The self.legend_handles_labels receives the patch as well."""
        ypos = 0.9
        km_arr = array(kms).reshape(-1,1)
        ypos_arr = array([ypos for x in kms]).reshape(-1,1)
        offsets = concatenate((km_arr, ypos_arr), axis=1)

        collection = RegularPolyCollection(
            numsides=4,
            rotation=0,
            sizes=(self.polysize,),
            facecolors=self.colormap(ypos),
            offsets=offsets,
            transOffset=self.bar_axes.transData,
            zorder=self.patch_zorder
        )
        self.bar_axes.add_collection(collection)
        
        line = Line2D((0,1),
                      (0,0),
                      linestyle='',
                      marker='D',
                      markersize=self.legend_markersize,
                      markeredgewidth=self.legend_markeredgewidth,
                      markerfacecolor=self.colormap(ypos))
        label = 'Overig'                               
        self.legend_handles.append(line)
        self.legend_labels.append(label)

    def add_uptriangles(self, kms):
        """Add upward triangles to bar_axes at specified kms.
        
        The self.legend_handles_labels receives the patch as well."""
        ypos = 0.7
        km_arr = array(kms).reshape(-1,1)
        ypos_arr = array([ypos for x in kms]).reshape(-1,1)
        offsets = concatenate((km_arr, ypos_arr), axis=1)

        collection = RegularPolyCollection(
            numsides=3,
            rotation=0,
            sizes=(self.polysize,),
            facecolors=self.colormap(ypos),
            offsets=offsets,
            transOffset=self.bar_axes.transData,
            zorder=self.patch_zorder
        )
        self.bar_axes.add_collection(collection)
        
        line = Line2D((0,1),
                      (0,0),
                      linestyle='',
                      marker='^',
                      markersize=self.legend_markersize,
                      markeredgewidth=self.legend_markeredgewidth,
                      markerfacecolor=self.colormap(ypos))
        label = 'Groene rivieren / ontrekkingen'                               
        self.legend_handles.append(line)
        self.legend_labels.append(label)

    def add_squares(self, kms):
        """Add squares to bar_axes at specified kms.
        
        The self.legend_handles_labels receives the patch as well."""
        ypos = 0.5
        km_arr = array(kms).reshape(-1,1)
        ypos_arr = array([ypos for x in kms]).reshape(-1,1)
        offsets = concatenate((km_arr, ypos_arr), axis=1)

        collection = RegularPolyCollection(
            numsides=4,
            rotation=pi/4,
            sizes=(self.polysize,),
            facecolors=self.colormap(ypos),
            offsets=offsets,
            transOffset=self.bar_axes.transData,
            zorder=self.patch_zorder
        )
        self.bar_axes.add_collection(collection)

        line = Line2D((0,1),
                      (0,0),
                      linestyle='',
                      marker='s',
                      markersize=self.legend_markersize,
                      markeredgewidth=self.legend_markeredgewidth,
                      markerfacecolor=self.colormap(ypos))
        label = 'Dijken / kades'
        self.legend_handles.append(line)
        self.legend_labels.append(label)

    def add_downtriangles(self, kms):
        """Add downward triangles to bar_axes at specified kms.
        
        The self.legend_handles_labels receives the patch as well."""
        ypos = 0.3
        km_arr = array(kms).reshape(-1,1)
        ypos_arr = array([ypos for x in kms]).reshape(-1,1)
        offsets = concatenate((km_arr, ypos_arr), axis=1)

        collection = RegularPolyCollection(
            numsides=3,
            rotation=pi,
            sizes=(self.polysize,),
            facecolors=self.colormap(ypos),
            offsets=offsets,
            transOffset=self.bar_axes.transData,
            zorder=self.patch_zorder
        )
        self.bar_axes.add_collection(collection)

        line = Line2D((0,1),
                      (0,0),
                      linestyle='',
                      marker='v',
                      markersize=self.legend_markersize,
                      markeredgewidth=self.legend_markeredgewidth,
                      markerfacecolor=self.colormap(ypos))
        label = 'Retentie'
        self.legend_handles.append(line)
        self.legend_labels.append(label)

    def add_circles(self, kms):
        """Add circles to bar_axes at specified kms.
        
        The self.legend_handles_labels receives the patch as well."""
        ypos = 0.1
        km_arr = array(kms).reshape(-1,1)
        ypos_arr = array([ypos for x in kms]).reshape(-1,1)
        offsets = concatenate((km_arr, ypos_arr), axis=1)

        collection = CircleCollection(
            sizes=(self.circlesize,),
            facecolors=self.colormap(ypos),
            offsets=offsets,
            transOffset=self.bar_axes.transData,
            zorder=self.patch_zorder
        )
        self.bar_axes.add_collection(collection)
        line = Line2D((0,1),
                      (0,0),
                      linestyle='',
                      marker='o',
                      markersize=self.legend_markersize,
                      markeredgewidth=self.legend_markeredgewidth,
                      markerfacecolor=self.colormap(ypos))
        label = 'Knelpunten'
        self.legend_handles.append(line)
        self.legend_labels.append(label)
        
    def add_text(self, kms, strs):
        ylim = self.axes.get_ylim()
        ypos = ylim[0] + (ylim[1] - ylim[0]) * 0.9
        for k,t in zip(kms, strs):
            self.axes.add_artist(Text(k,
                                      ypos,
                                      t,
                                      backgroundcolor='white',
                                      horizontalalignment='center'))
            self.axes.axvline(k,
                   color='#030303',
                   linestyle='--',
                   linewidth=1,
                   zorder=-10,
                   label='remove_from_legend')
            self.bar_axes.axvline(k,
                   color='#030303',
                   linestyle='--',
                   linewidth=1,
                   zorder=-10,
                   label=t)

    def legend(self, handles=None, labels=None):
        handles, labels = self.axes.get_legend_handles_labels()
        
        # Remove the labels from the vlines
        def f(tup):
            return tup[1] != 'remove_from_legend'
        handles, labels = zip(*filter(f, zip(handles, labels)))

        handles = list(handles)
        labels = list(labels)

        handles.extend(self.legend_handles)
        labels.extend(self.legend_labels)

        ncol = int(4 * self.width / 640)
        self.axes.legend(handles,
                         labels,
                         bbox_to_anchor=(0., 1.02, 1., .102),
                         loc=3,
                         ncol=ncol,
                         mode="expand",
                         borderaxespad=0.)
