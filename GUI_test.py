import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np
import sys
from collections import deque

# Define a class to manage the GUI, plotting, and updates
class LivePlotter:
    def __init__(self, win_title, plots_per_row=2):
        # Create the main Qt application (required for GUI)
        self.app = QtWidgets.QApplication(sys.argv)

        # Create a graphics layout widget which can hold multiple plots
        self.win = pg.GraphicsLayoutWidget(show=True, title=f"{win_title}")

        # Counter to track how many plots have been added
        self.plot_count = 0

        # Controls how many plots per row in the grid layout
        self.plots_per_row = plots_per_row

        self.data = {}      # Dictionary of numpy arrays, to store data for each plot
        self.curves = {}    # Dictionary of curve objects, to plot data
        self.interval_timers = {}    # Dictionary of interval timers (tells plot when to update)
        self.elapsed_timers = {} # Dictionary to hold elapsed timers for each plot (for x-axis)

    # Method to add a new plot to the layout
    def add_plot(self, title, x_axis, y_axis, buffer_size=100): #x_axis and y_axis are tuples (label, unit)
        # Move to the next row after a certain number of plots per row
        if self.plot_count % self.plots_per_row == 0 and self.plot_count > 0:
            self.win.nextRow()
        
        # Increment the plot counter
        self.plot_count += 1

        # Add a new plot with specified layout
        plot = self.win.addPlot(title=title)
        plot.setLabel('bottom', f'{x_axis[0]}', units=f'{x_axis[1]}')
        plot.setLabel('left', f'{y_axis[0]}', units=f'{y_axis[1]}')
        plot.showGrid(x=True, y=True)

        # Initialize data storage for the plot, using deque for O(1) complexity for appending and removing old data
        self.data[title] = [deque(maxlen=buffer_size), deque(maxlen=buffer_size)] #[x, y] deques

        # Add a curve (line) to the plot with yellow color
        curve = plot.plot(x=self.data[title][0], y=self.data[title][1], pen='y')

        #Store the curve object in the curves dictionary
        self.curves[title] = curve

    # Method to update a plot with new data
    def update(self, title):
        # Generate new data point (random number from a normal distribution)
        new_val_x = self.get_elapsed_time(title)
        new_val_y = np.random.randn(1)[0]

        x_data = self.data[title][0]  # Get the x-data deque for the plot
        y_data = self.data[title][1]  # Get the y-data deque for the plot

        #Append the new x, y to the deque lists
        x_data.append(new_val_x)
        y_data.append(new_val_y)

        #Plot the new data by updating the curve
        self.curves[title].setData(x=x_data, y=y_data)

    def get_elapsed_time(self, title):
        elapsed_timer = self.elapsed_timers.get(title)
        elapsed_time = elapsed_timer.elapsed() 
        return elapsed_time / 1000.0  # Convert milliseconds to seconds

    # Method to start a timer that periodically updates a specific plot
    def start_timer(self, title, interval_ms=100):
        # Create a new QTimer instance (interval timer, counts down in milliseconds)
        interval_timer = QtCore.QTimer()

        # Connect the timer's timeout signal to a lambda that calls self.update(title)
        interval_timer.timeout.connect(lambda: self.update(title))

        # Start the timer with the given interval (in milliseconds)
        interval_timer.start(interval_ms)

        # Store the interval timer in the interval timers dictionary to keep a reference to it
        # This prevents it from being garbage collected and allows later control (e.g., stopping)
        self.interval_timers[title] = interval_timer

        # Start a QElapsedTimer for this plot and store it in the elapsed timers dictionary
        elapsed = QtCore.QElapsedTimer()
        elapsed.start()
        self.elapsed_timers[title] = elapsed

    # Start the Qt application event loop
    def run(self):
        sys.exit(self.app.exec_())

# Entry point of the script
if __name__ == '__main__':
    # Create an instance of the live plotter
    plotter = LivePlotter("Test Live Plotter Window")

    #amount of time on a plot is measured by interval * buffer_size

    plotter.add_plot('Vessel Pressure', ('Time', 's'), ('Pressure','kPa'), buffer_size=100)
    plotter.start_timer('Vessel Pressure', interval_ms=100)

    plotter.add_plot('VMM Temperature', ('Time', 's'), ('Temperature','°C'), buffer_size=100)
    plotter.start_timer('VMM Temperature', interval_ms=100)

    # Run the GUI
    plotter.run()