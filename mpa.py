import numpy as np
import matplotlib.pyplot as plt
from PyQt4.QtGui import QFileDialog, QApplication
import os
import sys
from savitzky_golay import savitzky_golay

filename = "sample8/scan1.csv"

app = QApplication(sys.argv)
dlg = QFileDialog()
dlg.setFileMode(QFileDialog.AnyFile)
dlg.setFilter("Text files (*.txt)")
filename = dlg.getOpenFileName(filter="CSV files (*.csv)")
if filename == "":
    print "You need to choose a file"
    raise Exception

f = open(filename)

print "Opening: ", os.path.basename(filename), "\n"

# find scan data and read parameters
read_data = False       # this flag is set once the reading loop arrives
                        # at the actual scan data

X = []
Y = []
for num, line in enumerate(f):
    if read_data:
        toks = line.rstrip('\r\n').split(',')
        if len(toks) == 4:
            X.append(float(toks[0]))
            Y.append(float(toks[1]))
        continue
    if num == 0:
        if line != "Scan Parameters\r\r\n":
            print "File format not compatible, please open Dektak scan data CSV file"
            break
        else:
            print "Scan Parameters:\n================="
            continue
    if line == "Scan Data\r\r\n":
        print "\nFound scan data!"
        read_data = True
    else:
        if line.strip('\r\n\t ') != "":
            print line.rstrip('\r\n')
f.close()
X = np.asarray(X)
Y = np.asarray(Y)
orgY = np.copy(Y)

plt.figure()
line, = plt.plot(X, Y)
plt.xlabel("X [$\mu$m]")
plt.ylabel("Y [nm]")
plt.show()
plt.grid(b=True)
plt.xlim([np.min(X), np.max(X)])
plt.ylim([np.min(Y), np.max(Y)])

class Cursor(object):
    def __init__(self, ax):
        self.ax = ax
        self.marker = ax.axvspan(0, 1, facecolor='g', alpha=0.5)
        
        self.x1 = 0
        self.x2 = 0
        self.pressed = False

        # text location in axes coords
        self.txt = ax.text(0.7, 0.9, '', transform=ax.transAxes)

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
            plt.draw()
    
    def mouse_press(self, event):
        x = event.xdata
        self.update_x1(x)
        self.update_x2(x+1)
        self.pressed = True
        plt.draw()

    def mouse_release(self, event):
        x = event.xdata
        self.update_x2(x)
        self.pressed = False    
        plt.draw()

cursor1 = Cursor(plt.gca())
cursor2 = Cursor(plt.gca())

cids = []

def key_handler(event):
    if event.key == u'1':
        print "Cursor 1 activated"
        for cid in cids:
            plt.disconnect(cid)
        cids.append(plt.connect('motion_notify_event', cursor1.mouse_move))
        cids.append(plt.connect('button_press_event', cursor1.mouse_press))
        cids.append(plt.connect('button_release_event', cursor1.mouse_release))
    if event.key == u'2':
        print "Cursor 2 activated"
        for cid in cids:
            plt.disconnect(cid)
        cids.append(plt.connect('motion_notify_event', cursor2.mouse_move))
        cids.append(plt.connect('button_press_event', cursor2.mouse_press))
        cids.append(plt.connect('button_release_event', cursor2.mouse_release))
    if event.key == u'3':
        print "Leveling"
        if cursor1.x1 < cursor1.x2:
            mask1 = np.logical_and(X >= cursor1.x1, X <= cursor1.x2)
        else:
            mask1 = np.logical_and(X >= cursor1.x2, X <= cursor1.x1)
        if cursor2.x1 < cursor2.x2:
            mask2 = np.logical_and(X >= cursor2.x1, X <= cursor2.x2)
        else:
            mask2 = np.logical_and(X >= cursor2.x2, X <= cursor2.x1)

        print "cursor1: ", cursor1.x1, cursor1.x2       
        print "cursor2: ", cursor2.x1, cursor2.x2
       
        x1 = np.mean(X[mask1])
        x2 = np.mean(X[mask2])
        
        y1 = np.mean(Y[mask1])
        y2 = np.mean(Y[mask2])
        
        print "x1", x1, "x2", x2, "y1", y1, "y2", y2
        
        a = (y2-y1)/(x2-x1)
        b = 0.5*(y1+y2-a*(x1+x2))
        
        Y[:] = Y-a*X-b
        line.set_ydata(Y)
        plt.ylim([np.min(Y), np.max(Y)])
        plt.draw()
    if event.key == u'4':
        if cursor1.x1 < cursor1.x2:
            mask1 = np.logical_and(X >= cursor1.x1, X <= cursor1.x2)
        else:
            mask1 = np.logical_and(X >= cursor1.x2, X <= cursor1.x1)
        if cursor2.x1 < cursor2.x2:
            mask2 = np.logical_and(X >= cursor2.x1, X <= cursor2.x2)
        else:
            mask2 = np.logical_and(X >= cursor2.x2, X <= cursor2.x1)        
        
        y1 = np.mean(Y[mask1])
        y2 = np.mean(Y[mask2])        
        
        print "Average step height: ", y2-y1, " nm"
    if event.key == u'5':
        print "Savitzky Golay"
        Y[:] = savitzky_golay(Y, 77, 5)
        line.set_ydata(Y)
        plt.draw()
    if event.key == u'9':
        print "Cursors deactivated"
        for cid in cids:
            plt.disconnect(cid)
    if event.key == u'0':
        print "Reset"
        Y[:] = orgY
        line.set_ydata(Y)
        plt.ylim([np.min(Y), np.max(Y)])
        plt.draw()
        
        
    
plt.connect('key_press_event', key_handler)