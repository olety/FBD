#!/usr/local/bin/python3
# STL imports
import json
import logging
import os

# Package imports
import gmplot
import matplotlib.pyplot as plt
import numpy as np
from bokeh.io import output_file, show
from bokeh.models import (BoxSelectTool, Circle, ColumnDataSource, DataRange1d,
                          GMapOptions, GMapPlot, PanTool, WheelZoomTool)
from bokeh.plotting import figure
from sqlalchemy import desc, func

# Project imports
from fbd.storage import Event, Place, Storage


class Visualizer:
    def __init__(self, storage, working_folder='./vis_out'):
        self.storage = storage
        self.workplace = working_folder

    def _get_fpath(self, filename, delete_old=False):
        fpath = os.path.join(self.workplace, filename)
        if delete_old and os.path.isfile(fpath):
            os.remove(fpath)
        return fpath

    def plot_event_count(self, top=5):

        logging.debug('Visualizer - plot_event_count: Getting the data')
        to_plot = self.storage.session.query(
            Place.name,
            func.count(Place.name).label('total')).join(Event).group_by(
                Place.id).order_by(desc('total')).limit(top).all()

        logging.debug('Visualizer - plot_event_count: Creating subplots')
        fig, ax = plt.subplots()
        ind = np.arange(top)

        logging.debug(
            'Visualizer - plot_event_count: Extracting the plot data')
        names = ['\n'.join(item[0].split(' ')) for item in to_plot]
        vals = [item[1] for item in to_plot]

        logging.debug('Visualizer - plot_event_count: Plotting')
        width = 1.0 / (top - 3)
        ax.bar(ind, vals, width, align="center")
        plt.xticks(ind, names, fontsize=6)
        ax.set_title('Events per group')
        ax.set_ylabel('Events')

        logging.debug('Visualizer - plot_event_count: Showing the plot')
        plt.show()

    def plot_gmaps(self, filename='vis_out/gmap.html'):
        logging.debug('Visualizer - gmaps_plot: Requesting location')
        gmap = gmplot.GoogleMapPlotter.from_geocode('Wrocław')
        lats = []
        lngs = []

        logging.debug('Visualizer - gmaps_plot: Started processing places')
        for place in self.storage.session.query(Place).all():
            for i in range(len(place.events)):
                lats.append(place.lat)
                lngs.append(place.lon)
        logging.debug('Visualizer - gmaps_plot: Finished processing places')

        logging.debug('Visualizer - gmaps_plot: Started plotting')
        gmap.scatter(lats, lngs, '#3B0B39', size=40, marker=False)

        logging.debug('Visualizer - gmaps_plot: Started drawing')
        gmap.draw(self._get_fpath(filename, delete_old=True))

    def plot_gmaps_bokeh(self, api_key, filename='vis_out/bokeh.html'):

        lats = []
        lngs = []
        labels = []
        for place in self.storage.session.query(Place).all():
            for i in range(len(place.events)):
                lats.append(place.lat)
                lngs.append(place.lon)
                if place.topics:
                    labels.append(place.topics[0].name)
                else:
                    labels.append('Unknown')
        # TODO: Implement google map visualization
        # get top 4 place types
        # go from there
        # lat, lon = tools.get_coords('Wrocław')

        # map_options = GMapOptions(
        # lat=51.1, lng=17.03333, map_type="roadmap", zoom=11)

        # plot = GMapPlot(
        #     x_range=DataRange1d(), y_range=DataRange1d(), map_options=map_options, labels=labels
        # )
        # plot.title.text = "Wroclaw"

        # plot.api_key = api_key

        source = ColumnDataSource(data=dict(
            lat=lats,
            lon=lngs, ))

        p = figure(tools=['tap'])

        circle = Scatter(
            x='lon',
            y='lat',
            size=15,
            fill_color="blue",
            fill_alpha=0.8,
            line_color=None,
            legend=labels)

        p.add_glyph(source, circle)

        p.legend.location = "top_left"
        p.legend.click_policy = "hide"
        # output_file(filename)
        show(p)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    with open('google_api.json', 'r') as f:
        key = json.load(f)['key']

    s = Storage()
    v = Visualizer(s)
    # v.plot_gmaps()
    v.plot_gmaps_bokeh(key)
    # v.plot_event_count()
