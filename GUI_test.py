from pyqtgraph.Qt import QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np
from collections import deque
import sys

# Class to handle live plotting with individual start/stop buttons under each plot
class LivePlotter:
    def __init__(self, win_title, plots_per_row):
        # Create the main Qt application
        self.app = QtWidgets.QApplication(sys.argv)

        # Main window setup
        self.main_window = QtWidgets.QMainWindow()
        self.main_widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)
        self.main_window.setCentralWidget(self.main_widget)
        self.main_window.setWindowTitle(win_title)

        # Grid layout to place plot+button containers in rows/columns
        self.grid_layout = QtWidgets.QGridLayout()
        self.main_layout.addLayout(self.grid_layout)

        # Internal state tracking
        self.plot_count = 0                       # How many plots have been added
        self.plots_per_row = plots_per_row        # How many plots per row
        self.data = {}                            # title -> [x_deque, y_deque]
        self.curves = {}                          # title -> plot curve
        self.interval_timers = {}                 # title -> QTimer for updates
        self.elapsed_timers = {}                  # title -> QElapsedTimer for time axis
        self.running_state = {}                   # title -> bool: is plot running
        self.start_stop_buttons = {}              # title -> start/stop QPushButton
        self.save_data_buttons = {}               # title -> save data QPushButton

    # Add a new plot with button below it
    def add_plot(self, title, x_axis, y_axis, buffer_size):
        # Determine position in the grid layout
        row = self.plot_count // self.plots_per_row
        col = self.plot_count % self.plots_per_row
        self.plot_count += 1

        # Vertical layout to hold the plot and button
        container = QtWidgets.QVBoxLayout()

        # Create the plot widget
        plot_widget = pg.PlotWidget(title=title)
        plot_widget.setLabel('bottom', x_axis[0], units=x_axis[1])
        plot_widget.setLabel('left', y_axis[0], units=y_axis[1])
        plot_widget.showGrid(x=True, y=True)

        # Initialize circular buffers for x and y data
        self.data[title] = [deque(maxlen=buffer_size), deque(maxlen=buffer_size)]

        # Create the plot curve
        curve = plot_widget.plot(pen='y')  # yellow line
        self.curves[title] = curve

        # Create the start/stop button
        start_stop_button = QtWidgets.QPushButton(f"Stop {title}")
        start_stop_button.setStyleSheet("background-color: red;")
        start_stop_button.clicked.connect(lambda _, t=title: self.toggle_plot(t, buffer_size))
        self.start_stop_buttons[title] = start_stop_button

        # Create the save data button
        save_data_button = QtWidgets.QPushButton(f"Save {title} to CSV")
        save_data_button.clicked.connect(lambda _, t=title: self.save_data(t))
        self.save_data_buttons[title] = save_data_button

        # Add plot and button to vertical container
        container.addWidget(plot_widget)
        container.addWidget(start_stop_button)
        container.addWidget(save_data_button)

        # Wrap the layout in a QWidget and add it to the grid
        container_widget = QtWidgets.QWidget()
        container_widget.setLayout(container)
        self.grid_layout.addWidget(container_widget, row, col)

    # Update function: appends a new random data point and refreshes the plot
    def update(self, title):
        x_data, y_data = self.data[title]
        x_data.append(self.get_elapsed_time(title))
        y_data.append(np.random.randn())  # Replace with real data if desired
        self.curves[title].setData(x=x_data, y=y_data)

    # Return elapsed time in seconds since the plot started
    def get_elapsed_time(self, title):
        return self.elapsed_timers[title].elapsed() / 1000.0

    # Starts the QTimer that drives the updates for a given plot
    def start_timer(self, title, interval_ms):
        # Create a timer to update the plot regularly
        timer = QtCore.QTimer()
        timer.timeout.connect(lambda: self.update(title))
        timer.start(interval_ms)
        self.interval_timers[title] = timer

        # Start a timer to track elapsed time for the X-axis
        elapsed = QtCore.QElapsedTimer()
        elapsed.start()
        self.elapsed_timers[title] = elapsed

        # Mark the plot as running
        self.running_state[title] = True

    # Toggle between start and stop for a given plot
    def toggle_plot(self, title, buffer_size):
        if self.running_state[title]:
            # Stop the timer and update the button text
            self.interval_timers[title].stop()
            self.start_stop_buttons[title].setText(f"Start {title}")
            self.start_stop_buttons[title].setStyleSheet("background-color: green;")
            self.running_state[title] = False
        else:
            # Reset data and timer, restart updates
            self.data[title] = [deque(maxlen=buffer_size), deque(maxlen=buffer_size)]
            self.elapsed_timers[title].restart()
            self.interval_timers[title].start()
            self.start_stop_buttons[title].setText(f"Stop {title}")
            self.start_stop_buttons[title].setStyleSheet("background-color: red;")
            self.running_state[title] = True
    
    def save_data(self, title):
        print(f"Pretend I saved data for: {title}")
        
    # Show the window and start the event loop
    def run(self):
        self.main_window.show()
        sys.exit(self.app.exec_())

# Script entry point
if __name__ == '__main__':
    plotter = LivePlotter("Test Live Plotter", plots_per_row=4)

    # Add two plots with data update intervals
    plotter.add_plot(title='Vessel Pressure', x_axis=('Time', 's'), y_axis=('Pressure', 'kPa'), buffer_size=100)
    plotter.start_timer(title='Vessel Pressure', interval_ms=100)

    plotter.add_plot(title='VMM Temperature', x_axis=('Time', 's'), y_axis=('Temperature', '°C'), buffer_size=100)
    plotter.start_timer(title='VMM Temperature', interval_ms=100)

    # Launch the application
    plotter.run()