#!/usr/bin/python
from PyQt4 import QtGui
from PyQt4.QtCore import Qt, pyqtSignal, QObject, QFileInfo
import sys
import numpy as np
import matplotlib.pyplot as plt
import os

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

class Cursor(QObject):
    cursor_changed = pyqtSignal(float, float)

    def __init__(self, canvas, ax, color):
        super(Cursor, self).__init__()
        self.ax = ax
        self.canvas = canvas
        self.marker = ax.axvspan(0, 1, facecolor=color, alpha=0.0)    # marker invisible for now
        self.color = color

        self.x1 = 0.
        self.x2 = 0.
        self.pressed = False

    def update_x1(self, x1):
        self.x1 = x1
        coords = self.marker.get_xy()
        coords[0:2,0] = [x1, x1]
        coords[4,0] = x1
        self.marker.set_xy(coords)

    def update_x2(self, x2):
        self.x2 = x2
        coords = self.marker.get_xy()
        coords[2:4,0] = [self.x2, self.x2]
        self.marker.set_xy(coords)

    def mouse_move(self, event):
        if not event.inaxes:
            return
        x = event.xdata
        if self.pressed:
            self.update_x2(x)
            self.canvas.draw()
            self.cursor_changed.emit(self.x1, self.x2)

    def mouse_press(self, event):
        try:
            self.marker.remove()
        except ValueError: # in case the marker is already lost because new plot was created
            pass
        self.marker = self.ax.axvspan(0, 1, facecolor=self.color, alpha=0.5)
        x = event.xdata
        self.update_x1(x)
        self.update_x2(x+1)
        self.pressed = True
        self.canvas.draw()
        self.cursor_changed.emit(self.x1, self.x2)

    def mouse_release(self, event):
        x = event.xdata
        self.update_x2(x)
        self.pressed = False
        self.canvas.draw()
        self.cursor_changed.emit(self.x1, self.x2)

class MainWindow(QtGui.QMainWindow):
    def cursor_changed(self, x1, x2):
        if x1 < x2:
            mask1 = np.logical_and(self.X >= x1, self.X <= x2)
        else:
            mask1 = np.logical_and(self.X >= x2, self.X <= x1)

        avgX = np.mean(self.X[mask1])
        avgY = np.mean(self.Y[mask1])

        if self.sender() is self.cursor1:
            self.meas.setItem(0, 1, QtGui.QTableWidgetItem("%.2f nm"%avgY))
            self.cursor1_xavg = avgX
            self.cursor1_yavg = avgY
        elif self.sender() is self.cursor2:
            self.meas.setItem(1, 1, QtGui.QTableWidgetItem("%.2f nm"%avgY))
            self.cursor2_xavg = avgX
            self.cursor2_yavg = avgY
        self.meas.setItem(2, 1, QtGui.QTableWidgetItem("%.2f nm"%(self.cursor2_yavg-self.cursor1_yavg)))

    def level(self):
        x1, x2, y1, y2 = self.cursor1_xavg, self.cursor2_xavg, self.cursor1_yavg, self.cursor2_yavg
        a = (y2-y1)/(x2-x1)
        b = 0.5*(y1+y2-a*(x1+x2))

        self.Y -= a*self.X+b
        self.line.set_ydata(self.Y)
        #plt.ylim([np.min(Y), np.max(Y)])
        self.canvas.draw()

        # workaround to recalculate average x and average y with new levelling
        self.cursor1.cursor_changed.emit(self.cursor1.x1, self.cursor1.x2)
        self.cursor2.cursor_changed.emit(self.cursor2.x1, self.cursor2.x2)

    def revert(self):
        self.Y = np.copy(self.orgY)
        self.line.set_ydata(self.Y)
        self.canvas.draw()

        # workaround to recalculate average x and average y with new levelling
        self.cursor1.cursor_changed.emit(self.cursor1.x1, self.cursor1.x2)
        self.cursor2.cursor_changed.emit(self.cursor2.x1, self.cursor2.x2)

    def loadfile(self, filename):
        # find scan data and read parameters
        read_params = False     # this flag is set once the reading loop arrives
                                # at the scan parameters
        read_data = False       # this flag is set once the reading loop arrives
                                # at the actual scan data

        f = open(filename)

        X = []
        Y = []
        for num, line in enumerate(f):
            if num == 0:
                if line != "Scan Parameters\r\r\n":
                    break
                else:
                    self.scanpars.setRowCount(0) # empty the table
                    read_params = True
                    continue
            if read_params:
                if line == "Scan Data\r\r\n":
                    read_params = False
                    read_data = True
                    continue
                else:
                    stripped = line.strip('\r\n\t ')
                    if stripped != "":
                        toks = stripped.split(',', 1)
                        self.scanpars.insertRow(self.scanpars.rowCount())
                        self.scanpars.setItem(self.scanpars.rowCount()-1, 0, QtGui.QTableWidgetItem(toks[0]))
                        self.scanpars.setItem(self.scanpars.rowCount()-1, 1, QtGui.QTableWidgetItem(toks[1]))
            if read_data:
                toks = line.rstrip('\r\n').split(',')
                if len(toks) == 4:
                    X.append(float(toks[0]))
                    Y.append(float(toks[1]))
                continue
        f.close()
        if not read_data:
            # reset window
            self.scanpars.setRowCount(0)
            self.meas.clear()
            self.ax.clear()
            self.setWindowTitle('Mercury Profile Analyser')
            QtGui.QMessageBox.critical(self, 'Error', 'The file could not be loaded')
        self.setWindowTitle('Mercury Profile Analyser [%s]'%QFileInfo(filename).baseName())
        self.X = np.asarray(X)
        self.Y = np.asarray(Y)
        self.orgY = np.copy(Y)

        self.ax.clear()
        self.line, = self.ax.plot(X, Y)
	self.ax.grid(True)
        self.ax.set_xlabel('distance x [$\mu$m]')
        self.ax.set_ylabel('height y [nm]')
        self.canvas.draw()

    def open_handler(self):
        dlg = QtGui.QFileDialog()
        dlg.setFileMode(QtGui.QFileDialog.AnyFile)
        dlg.setFilter("Text files (*.txt)")
        filename = dlg.getOpenFileName(filter="CSV files (*.csv)", directory=self.last_path)
        if filename != '':
            self.last_path = QFileInfo(filename).path()
            self.loadfile(filename)

    def activate_cursor1(self):
        for cid in self.cids:
            self.canvas.mpl_disconnect(cid)
        self.cids = []
        self.cids.append(self.canvas.mpl_connect('motion_notify_event', self.cursor1.mouse_move))
        self.cids.append(self.canvas.mpl_connect('button_press_event', self.cursor1.mouse_press))
        self.cids.append(self.canvas.mpl_connect('button_release_event', self.cursor1.mouse_release))

    def activate_cursor2(self):
        for cid in self.cids:
            self.canvas.mpl_disconnect(cid)
        self.cids = []
        self.cids.append(self.canvas.mpl_connect('motion_notify_event', self.cursor2.mouse_move))
        self.cids.append(self.canvas.mpl_connect('button_press_event', self.cursor2.mouse_press))
        self.cids.append(self.canvas.mpl_connect('button_release_event', self.cursor2.mouse_release))

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.setWindowTitle('Mercury Profile Analyser')
        self.last_path = ''

        self.cids = []

        self.X = np.zeros(1)
        self.Y = np.zeros(1)
        self.orgY = np.copy(self.Y)

        exitAction = QtGui.QAction(QtGui.QIcon.fromTheme("application-exit"), 'Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(QtGui.qApp.quit)

        openAction = QtGui.QAction(QtGui.QIcon.fromTheme("document-open"), 'Open', self)
        openAction.setShortcut('Ctrl+O')
        openAction.triggered.connect(self.open_handler)

        path = os.path.dirname(os.path.realpath(__file__))
        cursor1Action = QtGui.QAction(QtGui.QIcon(path+'/cursor1.png'), 'Cursor 1', self)
        cursor1Action.setShortcut('Ctrl+1')
        cursor1Action.triggered.connect(self.activate_cursor1)

        cursor2Action = QtGui.QAction(QtGui.QIcon(path+'/cursor2.png'), 'Cursor 2', self)
        cursor2Action.setShortcut('Ctrl+2')
        cursor2Action.triggered.connect(self.activate_cursor2)

        levelAction = QtGui.QAction(QtGui.QIcon(path+'/level.png'), 'Cursor 2', self)
        levelAction.setShortcut('Ctrl+L')
        levelAction.triggered.connect(self.level)

        revertAction = QtGui.QAction(QtGui.QIcon.fromTheme("document-revert"), 'Revert', self)
        revertAction.setShortcut('Ctrl+R')
        revertAction.triggered.connect(self.revert)

        self.toolbar = self.addToolBar('Toolbar')
        self.toolbar.addAction(exitAction)
        self.toolbar.addAction(openAction)
        self.toolbar.addAction(cursor1Action)
        self.toolbar.addAction(cursor2Action)
        self.toolbar.addAction(levelAction)
        self.toolbar.addAction(revertAction)

        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.setCentralWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)
        self.cursor1 = Cursor(self.canvas, self.ax, 'r')
        self.cursor2 = Cursor(self.canvas, self.ax, 'g')
        self.cursor1_xavg = 0.
        self.cursor1_yavg = 0.
        self.cursor2_xavg = 0.
        self.cursor2_yavg = 0.
        self.cursor1.cursor_changed.connect(self.cursor_changed)
        self.cursor2.cursor_changed.connect(self.cursor_changed)

        self.scanpars = QtGui.QTableWidget(0, 2)
        self.scanpars.verticalHeader().hide()
        self.scanpars.horizontalHeader().setStretchLastSection(True)
        self.scanpars.setHorizontalHeaderLabels(['Name', 'Value'])

        self.meas = QtGui.QTableWidget(3, 2)
        self.meas.verticalHeader().hide()
        self.meas.horizontalHeader().hide()
        self.meas.horizontalHeader().setStretchLastSection(True)
        self.meas.setItem(0, 0, QtGui.QTableWidgetItem('Cursor 1 avg'))
        self.meas.setItem(1, 0, QtGui.QTableWidgetItem('Cursor 2 avg'))
        self.meas.setItem(2, 0, QtGui.QTableWidgetItem('ASH'))

        scanpars_dock = QtGui.QDockWidget('Scan parameters', self)
        scanpars_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        scanpars_dock.setWidget(self.scanpars)
        self.addDockWidget(Qt.LeftDockWidgetArea, scanpars_dock)

        meas_dock = QtGui.QDockWidget('Measurements', self)
        meas_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        meas_dock.setWidget(self.meas)
        self.addDockWidget(Qt.LeftDockWidgetArea, meas_dock)

        self.setGeometry(300, 300, 800, 600)
        self.show()

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)

    mainwindow = MainWindow()

    # Start the main loop.
    ret = app.exec_()

    sys.exit(ret)
