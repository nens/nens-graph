Changelog of nens-graph
===================================================


0.4 (unreleased)
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
