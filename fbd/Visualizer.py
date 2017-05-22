#!/usr/local/bin/python3
import gmplot
import logging
import os
import numpy as np
from storage import Storage, Place, Event


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
        from sqlalchemy import func, desc
        import matplotlib.pyplot as plt

        logging.debug('Visualizer - plot_event_count: Getting the data')
        to_plot = self.storage.session.query(
            Place.name, func.count(Place.name).label('total')).join(Event).group_by(Place.id).order_by(desc('total')).limit(top).all()

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

    def plot_gmaps(self, filename='gmap.html'):
        # TODO: Add filters and popups to the generated plot
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


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    s = Storage()
    v = Visualizer(s)
    v.plot_gmaps()
    # v.plot_event_count()
