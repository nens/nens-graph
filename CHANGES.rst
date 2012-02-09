Changelog of nens-graph
===================================================


0.6 (unreleased)
----------------

- Nothing changed yet.


0.5.2 (2012-02-09)
------------------

- Changed MARGIN_LEFT from 96 to 104.


0.5.1 (2012-02-08)
------------------

- Fixed buildout config.

- Fixed bug using stacked bars.


0.5 (2012-02-07)
----------------

- Moved DateGridGraph from lizard-graph to here.


0.4.5 (2011-11-21)
------------------

- Added MANIFEST.in for making packages.


0.4.4 (2011-11-21)
------------------

- Added new scales: RestrictToMonthScale, MercatorLatitudeScale.

- Added kwarg response to NensGraph.png_response to make it more flexible.


0.4.3 (2011-10-06)
------------------

- Used latest layout system for opendap graph, inspired by rainappgraph

- Added dedicated method for getting bbox of ticklabels, since the general way
  didn't work.

- Made the truncation length of legend labels a little larger


0.4.2 (2011-10-06)
------------------

- Put legend back in place


0.4.1 (2011-10-05)
------------------

- Adjusted Opendap graph so that it does not define locator and formatter if the
  restrict_to_month keyword is present.


0.4 (2011-09-30)
----------------

- Nothing changed yet.


0.3.1 (2011-09-19)
------------------

- Added use of tz kwarg in Rainapp graph


0.3 (2011-09-07)
----------------

- Changed RainappGraph.legend() so that it adds a legend object to the graph.

- Moved handling of figure width and height to common.NensGraph


0.2 (2011-09-01)
----------------

- Cleaned up rainapp graph. It is now only intended for a barchart of
  precipitation data.

- Implemented a custom ylim calculation and setting for barcharts.

- Set lower ylim to -1% and ylim max to at least 1 mm in rainapp.


0.1 (2011-08-30)
----------------

- Changed signature of NensGraph.on_draw()

- Added RainappGraph

- Added pixel-to-figure-coordinates methods for NensGraph class

- Added methods to find out width and height of specific plot objects at drawing
  time


0.0.1 (2011-05-18)
------------------

- Initial library skeleton created by nensskel.

- Copied orinal lizard-map.adapter.graph to basic.

- Added common graph class and deltaportaal-specific river graph
