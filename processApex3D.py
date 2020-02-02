#!/usr/bin/python3
# -*- coding: utf-8 -*- apex3DNavigator.py
"""
@author: Guillaume van der Rest
Extract relevant points, perform CCS calibration and display result
from Apex3D Data,
This is the Data class which handles data management
"""
import pandas as pd
import numpy as np

class CCS_Data(object):
    """This class holds the data loaded from the Apex3D file and performs all 
    the necessary processing.
    """
    # For now only consider n H+ type ions. This should be fixed in a better way.
    m_charge_ion = 1.00727645
    
    def read(self, csv_file):
        """Load the data from a csv file.
        
        Args:
            csv_file (str): Path to the file to be read from.
        """
        self.data = pd.read_csv(csv_file)

    def save(self,  csv_file):
        """Save data with series to a csv file
        
        Args:
            csf_file (str): Path to the file to be written to.
        """
        self.data_CCS.to_csv(csv_file, sep='\t', decimal=',')
        
    def process(self, parameters):
        """Process the data to keep only values which fall within a defined m/z range.
        Directly convert the values to absolute collision cross-sections.
        
        Args:
            parameters (dict): Parameters passed from the UI for processing.
        """
        # Stage 1: extract only the lines for which m/z falls within acceptable range
        result_set = []
        for i in range(parameters['MinCS'], parameters['MaxCS']+1):
            mz = (parameters['M'] + i * self.m_charge_ion) / i
            mz_min = mz * (1 - parameters['ppm']/1000000)
            mz_max = mz * (1 + parameters['ppm']/1000000)
            filtered_table = self.data[(self.data['m_z'] > mz_min) & (self.data['m_z'] < mz_max)  & (self.data['inten']>2000)]
            filtered_table['z'] = i
            result_set.append(filtered_table)
        fdata = pd.concat(result_set)
        mu = parameters['M']*parameters['gas']/(parameters['M']+parameters['gas'])
        self.data_CCS = fdata.assign(CCS = lambda x : (parameters['a'] * 
                                           (((x['rt'] *
                                           parameters['push'] / 1000) - 
                                           parameters['C'] * np.sqrt(x['m_z'] /1000))**parameters['X'])*x['z']/np.sqrt(mu)),
                         Log_Intensity = lambda x : (np.log10(x['inten'])))
        self.data_CCS['Selected'] = False
        self.data_CCS['Series'] = 0

    def plot(self, axes):
        """Plot the data on a matplotlib axes.
        
        Args:
            axes(Matplotlib.Axes): the matplotlib axes on which the data should be drawn.
        """
        self.data_CCS.plot.scatter(x='z', y='CCS', c='Log_Intensity', s=50, picker=True, colormap='hot_r', ax=axes)
        
    def num_points(self):
        """Returns the number of points in the data set
        """
        return self.data_CCS.shape[0]
          
    def toggleSelected(self, point, series,  axes):
        """Toggle the selection status of a given point, and update the drawing accordingly.
        The collection to replot is assumed to be the top-most collection, which should
        be automatically done when a change in series occurs.
        
        Args:
            point (int): index of the selected point
            series (int) : currently active series
            axex (Matplotlib.Subplot.Axes): axes containing the collection to be updated.
            
        Returns the position at which the series is laid out, or if empty 0.
        """
        # Do we have an empty set to start with?
        oldEmptySet = (self.data_CCS[self.data_CCS['Selected']]).empty
        index = self.data_CCS.index[point]
        self.data_CCS.loc[index, 'Selected'] = not self.data_CCS.loc[index, 'Selected']
        if not oldEmptySet:
            axes.collections.pop()
            axes.figure.canvas.draw_idle()
        return self.plotSelectedOnTop(series,  axes)
 
    def plotSelectedOnTop(self, series,  axes):
        newEmptySet = (self.data_CCS[self.data_CCS['Selected']]).empty
        if not newEmptySet:
            self.data_CCS[self.data_CCS['Selected']].plot.scatter(x='z', y='CCS', s=50, 
                        color=(['k','r','g','b','c','m','y'][series % 7]), 
                        ax=axes)
            axes.figure.canvas.draw_idle()
            return len(axes.collections) - 1
        return 0
            
    def saveSeries(self,  series):
        """Sets data_CCS for the selected series to the value series.
        
        Args:
            series (int): value of the series to update to.
        """
        self.data_CCS.loc[self.data_CCS['Selected'],'Series'] = series
        self.data_CCS['Selected'] = False
          
    def updatePlotSeries(self, currentSeries,  layers,  ax):
        """When changing to a new series, we need to update the plot in order to
        have the current series plot on top of all the others.
        We also maintain a global list which holds the layers of each series plot
        on the plot axes.
        
        Args:
            currentSeries (int): series number to put on top
            layers ([int]): list of the series plotted on axes, back to front.
            ax (Matplotlib.Plot.Axes) : axes on which the collections are laid.
            
        Returns the position of the replotted series on the collection.
        0 if the series is empty (and thus not plotted).
        """
        # Start by restoring the selection state.
        self.data_CCS.loc[self.data_CCS['Series']  == currentSeries,  'Selected'] \
            = True
        # Position can be non zero with an empty set if the point has been 
        # claimed by a other series and the current series was not made active.
        # So first we should check this.
        if currentSeries in layers:
            pos = layers.index(currentSeries)
            if pos:
                ax.collections.pop(pos)
                layers.remove(currentSeries)
        return self.plotSelectedOnTop(currentSeries,  ax)
            
# Output_Series table related functions
    # Functions to process data
    def numPtsSel(self, default):
        return len(self.data_CCS[self.data_CCS['Selected']])
    
    def totalIntSel(self,  default):
        return ((self.data_CCS[self.data_CCS['Selected']])['inten']).sum()
    
    def ratioIntSel(self,  default):
        try:
            result = self.totalIntSel(default) / (self.data_CCS['inten']).sum()
        except ValueError:
            return default
        return result * 100
        
    def averagezSel(self,  default):
        num_pts = self.numPtsSel(default)
        if not num_pts:
            return default
        return ((self.data_CCS[self.data_CCS['Selected']])['z']).sum() / num_pts
    
    def averageCCSSel(self,  default):
        num_pts = self.numPtsSel(default)
        if not num_pts:
            return default
        return ((self.data_CCS[self.data_CCS['Selected']])['CCS']).sum() / num_pts
    
    def wAvzSel(self,  default):
        total_int = self.totalIntSel(default)
        if not total_int:
            return default
        return ((self.data_CCS[self.data_CCS['Selected']])['z'] 
                        * (self.data_CCS[self.data_CCS['Selected']])['inten']).sum()  \
                        / total_int
    
    def wAvCCSSel(self,  default):
        total_int = self.totalIntSel(default)
        if not total_int:
            return default
        return ((self.data_CCS[self.data_CCS['Selected']])['CCS'] 
                        * (self.data_CCS[self.data_CCS['Selected']])['inten']).sum() \
                        / total_int
                        
    def getSelectedDataStats(self):
     # Dictionnary of rows, in the form label : (function, default_val)
        return ( 
            ("Number of points",  self.numPtsSel(0)), 
            ("Total intensity",  self.totalIntSel(0)), 
            ("Ratio of intensity (%)",  self.ratioIntSel(0)), 
            ("Average z",  self.averagezSel("N/A")), 
            ("Average CCS",  self.averageCCSSel("N/A")), 
            ("Weighted average z", self.wAvzSel("N/A")), 
            ("Weighted average CCS",  self.wAvCCSSel("N/A"))
            )
