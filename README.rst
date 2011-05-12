nens-graph
==========================================

Nens-graph is a separate library of custom matplotlib graphs for use
in the lizard-framework.

The graph layout should be controlled in the library, and only the data
should be added in the calling Django application. Common classes useful
for other graphs go in common.py, stuff changing from graph to graph should
be in eachs graphs own class.
