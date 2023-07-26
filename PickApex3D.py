#!/usr/bin/python3
# -*- coding: utf-8 -*- PickApex3D.py
"""
@author: Guillaume van der Rest
Extract relevant points, perform CCS calibration and display result
from Apex3D Data,
"""

from PyQt5 import QtGui, QtWidgets,  QtCore
import sys
from matplotlib.figure import Figure
from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)
from locale import atof,  atoi,  str as lstr

from Ui_PickApex3D import Ui_PickApex3D
from processApex3D import CCS_Data

class PickApex3D(QtWidgets.QMainWindow, Ui_PickApex3D):
    def __init__(self):
        super().__init__()

        # Set up the user interface from Designer.
        self.setupUi(self)
        self.currentSeries = 1
        
        # Set sensible initial values in the UI.
        # These have to be localized, so we must set them here.
        self.setInitialUIvalues()
        # Setup and connect the canvas from matplotlib
        self.canvas = self.makeFigureCanvas(self.display_frame)
        # Setup the connections        
        self.setInputValidation()
        self.makeConnections()
        
        self.statusbar.showMessage('Ready')

    # Set up the matplotlib canvas in the display_frame widget
    def makeFigureCanvas(self, frame):
        self.fig = Figure((10.0, 8.0), dpi=50)
        canvas = FigureCanvas(self.fig)
        canvas.setParent(frame)
        canvas.setFocus()
        self.mpl_toolbar = NavigationToolbar(canvas, frame)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(canvas)
        vbox.addWidget(self.mpl_toolbar)
        frame.setLayout(vbox)
        return canvas

    def setInputValidation(self):
        ispositivedouble=QtGui.QDoubleValidator()
        isdouble=QtGui.QDoubleValidator()
        ispositivedouble.setBottom(0)
        ispositiveint=QtGui.QIntValidator()
        ispositiveint.setBottom(0)
        self.NeutralMass.setValidator(ispositivedouble)
        self.MassAccuracy.setValidator(ispositivedouble)
        self.MinCS.setValidator(ispositiveint)
        self.MaxCS.setValidator(ispositiveint)
        self.Calibration_a.setValidator(isdouble)
        self.Calibration_b.setValidator(isdouble)
        self.Calibration_X.setValidator(isdouble)
        self.TransferParam.setValidator(ispositivedouble)
        self.PusherDelay.setValidator(ispositivedouble)
        self.Gas_mass.setValidator(ispositivedouble)

    def setInitialUIvalues(self):
        self.NeutralMass.setText(lstr(22870))
        self.MassAccuracy.setText(lstr(200))
        self.MinCS.setText(lstr(1))
        self.MaxCS.setText(lstr(50))
        self.Calibration_a.setText(lstr(231.7))
        self.Calibration_b.setText(lstr(118.7))
        self.Calibration_X.setText(lstr(0.6262))
        self.TransferParam.setText(lstr(1.41))
        self.PusherDelay.setText(lstr(110))
        self.Gas_mass.setText(lstr(28))

    # Connections go here
    def makeConnections(self):
        self.actionLoad_Data_File.triggered.connect(self.openandPlot)
        self.actionSave_processed.triggered.connect(self.storeData)
        self.actionQuit.triggered.connect(self.close)
        self.actionNext_series.triggered.connect(self.nextSeries)
        self.actionPrevious_series.triggered.connect(self.prevSeries)
        self.canvas.mpl_connect('key_press_event', self.on_key_press)

    # Functions for connectSlotsByName() called by Ui from pyuic5
    @QtCore.pyqtSlot(int)
    def on_selectSeries_valueChanged(self,  i):
        """Catches a change in the selectSeries spin box.
        
        Args: 
            i : new value for the series
        """
        self.updateSeries(i)
        
    # Most function actions go here.

    def on_key_press(self, event):
        # implement the default mpl key press events described at
        # http://matplotlib.org/users/navigation_toolbar.html#navigation-keyboard-shortcuts
        key_press_handler(event, self.canvas, self.mpl_toolbar)

    def openandPlot(self):
        # All values should be set before loading a data file. Check if it is the case.
        try: 
            params = self.validate_param()
        except ValueError :
            self.statusbar.showMessage('Invalid value for parameters.')
            raise         
        self.statusbar.showMessage('Opening file')
        csv_file_list = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', '/home', '*.csv')
        if len(csv_file_list) > 2 :
            # Output a warning that we will not handle more than one file.
            self.statusbar.showMessage('Only opening the first file.')
        csv_file = csv_file_list[0]
        if csv_file == '' :
            self.statusbar.showMessage('Ready')
            return True
        self.data = CCS_Data()
        try:
            self.data.read(csv_file)
        except:
            self.statusbar.showMessage('Error reading file: ' + csv_file)
            return True
        try:
            self.data.process(params)
        except KeyError:
            self.statusbar.showMessage('Error processing file: ' + csv_file)
            raise
        if self.data.num_points() == 0:
            self.statusbar.showMessage('No matching data points found in:'
            + csv_file)
            return True         
        self.fig.clear()
        self.currentSeries = 1
        self.ax  = self.fig.add_subplot(111)
        self.plotLayers = { 'main' : self.data.plot(self.ax),  1 : None }
        self.fig.canvas.mpl_connect('pick_event', self.onpick)
        self.canvas.draw()
  
        # Make the selectSeries spinBox active and set its initial value as its limits to 
        # sensible values.
        self.selectSeries.setEnabled(True)
        self.selectSeries.setMinimum(1)
        self.selectSeries.setMaximum(1)
        self.selectSeries.setValue(1)
        # Initialize the output values for the series.
        self.updateSeriesTable()
 
    def storeData(self):
        csv_file_list = QtWidgets.QFileDialog.getSaveFileName(self, 'Store result in"', '/home', '*.csv')
        if len(csv_file_list) > 2 :
        # Output a warning that we will not handle more than one file.
            self.statusbar.showMessage('Only saving to the first file.')
        csv_file = csv_file_list[0]
        if csv_file == '' :
            self.statusbar.showMessage('Ready')
            return True
        self.updateSeries(self.currentSeries)
        try:
            self.data.save(csv_file)
        except IOError as err:
            self.statusbar.showMessage('Unable to write file:' + err)
            return True
        self.statusbar.showMessage('Saved to file ' + csv_file)
        return True
        
    def onpick(self, event):
        self.data.toggleSelected(event.ind[0],  self.plotLayers,  self.currentSeries,  self.ax)
        self.updateSeriesTable()

    def validate_param(self):
        try:
            prm = dict(a=atof(self.Calibration_a.text()), b=atof(self.Calibration_b.text()),
                       X=atof(self.Calibration_X.text()), C=atof(self.TransferParam.text()),
                       push=atof(self.PusherDelay.text()), gas=atof(self.Gas_mass.text()),
                       M=atof(self.NeutralMass.text()), ppm=atof(self.MassAccuracy.text()))
        except ValueError:
            raise
        if self.MinCS.text == '':
            prm['MinCS']=1
        else:
            try:
                prm['MinCS'] = atoi(self.MinCS.text())
            except ValueError:
                raise
        if self.MaxCS.text == '':
            prm['MaxCS']=prm['MinCS']
        else:
            try:
                prm['MaxCS'] = atoi(self.MaxCS.text())
            except ValueError:
                raise
        if prm['MaxCS'] < prm['MinCS']:
            tmp_min = prm['MaxCS']
            prm['MaxCS'] = prm['MinCS']
            prm['MinCS'] = tmp_min
        return prm

    def updateSeries(self, newseries):
        self.data.saveSeries(self.currentSeries)
        self.currentSeries = newseries
        self.data.updatePlotSeries(self.currentSeries,  self.plotLayers,  self.ax)
        # Failsafe: should not happen because updateSeries is only called by
        # the selectSeries.valueChanged() signal and by saving the file which
        # does not change the series.
        if self.currentSeries != self.selectSeries.value():
            self.selectSeries.setValue(self.currentSeries)
        self.updateSeriesTable()

    def updateSeriesTable(self):
        self.Output_Series.clear()
        selectedDataStats = self.data.getSelectedDataStats()
        self.Output_Series.setRowCount(len(selectedDataStats))
        self.Output_Series.setColumnCount(2)
        for row,  val in enumerate(selectedDataStats):
            label,  value = val
            title = QtWidgets.QTableWidgetItem(label)
            self.Output_Series.setItem(row, 0, title)
            if not isinstance(value,  str):
                value = lstr(value)
            value = QtWidgets.QTableWidgetItem(value)
            self.Output_Series.setItem(row,  1,  value)
        self.Output_Series.resizeColumnsToContents()

    def nextSeries(self):
        if self.currentSeries >= self.selectSeries.maximum() :
            self.selectSeries.setMaximum(self.currentSeries+1)
            self.plotLayers[self.currentSeries+1] = None
        self.selectSeries.setValue(self.currentSeries+1)

    def prevSeries(self):
        if self.currentSeries > 1:
            self.selectSeries.setValue(self.currentSeries-1)
            
def main():
    
    app = QtWidgets.QApplication(sys.argv)
    mw = PickApex3D()
    mw.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
