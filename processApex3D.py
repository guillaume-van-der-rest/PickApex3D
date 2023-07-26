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
            filtered_table = filtered_table.assign(z = i)
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
        return self.data_CCS.plot.scatter(x='z', y='CCS', c='Log_Intensity', s=50, picker=True, colormap='hot_r', ax=axes)
        
    def num_points(self):
        """Returns the number of points in the data set
        """
        return self.data_CCS.shape[0]
          
    def toggleSelected(self, point, layers, series,  axes):
        """Toggle the selection status of a given point, and update the drawing accordingly.
        The collection to replot is assumed to be the top-most collection, which should
        be automatically done when a change in series occurs.
        
        Args:
            point (int): index of the selected point
            layers (dict of Artists): a dictionnary of the plots
            series (int) : currently active series
            axes (Matplotlib.Subplot.Axes): axes containing the collection to be updated.
        """
        # Do we have an empty set to start with?
        index = self.data_CCS.index[point]
        self.data_CCS.loc[index, 'Selected'] = not self.data_CCS.loc[index, 'Selected']
        if layers[series] is not None :
            layers[series].remove()
        layers[series] = self.plotSelectedOnTop(layers,  series,  axes)
        axes.figure.canvas.draw_idle()
 
    def plotSelectedOnTop(self, layers,  series,  axes):
        if not (self.data_CCS[self.data_CCS['Selected']]).empty :
            result = axes.scatter('z',  'CCS',  data=self.data_CCS[self.data_CCS['Selected']], s=50, 
                        color=(['k','r','g','b','c','m','y'][series % 7]))
            # Make sure it is on top.  
            result.set_zorder(len(layers))
            return result
        return None
            
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
        
        Args:
            currentSeries (int): series number to put on top
            layers (dict of Artists): dictionnary of the series plotted on axes, not ordered.
            ax (Matplotlib.Plot.Axes) : axes on which the collections are laid.
            
        """
        # Start by restoring the selection state.
        self.data_CCS['Selected'] = False
        self.data_CCS.loc[self.data_CCS['Series']  == currentSeries,  'Selected'] \
            = True
        # Set the zorder of all the series except the current one to their default position.
        for keys in layers :
            if layers[keys] is not None :
                if isinstance(keys,  int)  :
                    layers[keys].set_zorder(keys)
                else :
                    layers[keys].set_zorder(0)
        if layers[currentSeries] is not None :
            layers[currentSeries].remove()
        layers[currentSeries] = self.plotSelectedOnTop(layers,  currentSeries,  ax)
        ax.figure.canvas.draw_idle()
            
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
