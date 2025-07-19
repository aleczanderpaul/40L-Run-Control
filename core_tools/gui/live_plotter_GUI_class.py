from pyqtgraph.Qt import QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np
import sys
import pandas as pd
from .get_data_for_GUI import get_n_XY_datapoints
import subprocess
import shlex
import platform

'''Class to handle live plotting and add various controls/buttons in a Qt GUI application.'''

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

        # Internal state tracking for plots
        self.plot_count = 0                       # How many plots have been added
        self.plots_per_row = plots_per_row        # How many plots per row
        self.data = {}                            # title -> {x: pandas Series, y: pandas Series, buffer_size: int}
        self.curves = {}                          # title -> plot curve
        self.interval_timers = {}                 # title -> QTimer for updates
        self.elapsed_timers = {}                  # title -> QElapsedTimer for time axis
        self.running_state = {}                   # title -> bool: is plot running
        self.start_stop_buttons = {}              # title -> start/stop QPushButton
        self.csv_filepath = {}                    # title -> CSV filepath from logging to pull data from
        self.datatype = {}                        # Datatype for the plots (e.g., 'pressure', 'temperature')

        #Internal state tracking for command buttons
        self.cmd_buttons = {}                     # title -> QPushButton for terminal commands
        self.cmd_processes = {}                   # title -> subprocess.Popen object for running commands
        self.cmd_running_state = {}               # title -> bool: is command running

    # Add a new plot with button below it
    def add_plot(self, title, x_axis, y_axis, buffer_size, csv_filepath, datatype): #x_axis and y_axis are tuples of (label, unit), and buffer_size is the number of data points to display at once
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
        self.data[title] = {"x": pd.Series(np.full(buffer_size, np.nan), name='x'), "y": pd.Series(np.full(buffer_size, np.nan), name='y'), "buffer_size": buffer_size}

        #Store the filepath of the CSV associated with this plot
        self.csv_filepath[title] = csv_filepath

        # Store the datatype for this plot
        self.datatype[title] = datatype

        # Create the plot curve
        curve = plot_widget.plot(pen='y')  # yellow line
        self.curves[title] = curve

        # Create the start/stop button
        start_stop_button = QtWidgets.QPushButton(f"Stop {title}")
        start_stop_button.setStyleSheet("background-color: red;")
        start_stop_button.clicked.connect(lambda _, t=title: self.toggle_plot(t, buffer_size))
        self.start_stop_buttons[title] = start_stop_button

        # Add plot and button to vertical container
        container.addWidget(plot_widget)
        container.addWidget(start_stop_button)

        # Wrap the layout in a QWidget and add it to the grid
        container_widget = QtWidgets.QWidget()
        container_widget.setLayout(container)
        self.grid_layout.addWidget(container_widget, row, col)

    # Update function: appends a new random data point and refreshes the plot
    def update(self, title):
        x_data, y_data, buffer_size = self.data[title]["x"], self.data[title]["y"], self.data[title]["buffer_size"]
        csv_filepath = self.csv_filepath[title]
        datatype = self.datatype[title]
        x_data, y_data = get_n_XY_datapoints(csv_filepath, buffer_size, datatype)
        self.curves[title].setData(x=x_data, y=y_data)

    # Return elapsed time in seconds since the plot started
    def get_elapsed_time(self, title):
        return self.elapsed_timers[title].elapsed() / 1000.0 #convert ms to seconds

    # Starts the QTimer that drives the updates for a given plot
    def start_timer(self, title, interval_ms):
        # Create a timer to update the plot regularly
        timer = QtCore.QTimer()
        timer.timeout.connect(lambda: self.update(title))
        timer.start(interval_ms)
        self.interval_timers[title] = timer

        # Start a timer to track elapsed time
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
            self.data[title] = {"x": pd.Series(np.full(buffer_size, np.nan), name='x'), "y": pd.Series(np.full(buffer_size, np.nan), name='y'), "buffer_size": buffer_size}
            self.elapsed_timers[title].restart()
            self.interval_timers[title].start()
            self.start_stop_buttons[title].setText(f"Stop {title}")
            self.start_stop_buttons[title].setStyleSheet("background-color: red;")
            self.running_state[title] = True

    #Run a terminal command using subprocess
    def run_terminal_command(self, title, command):
        system = platform.system()

        if system == 'Windows':
            #Use shlex.split to safely split the command respecting shell syntax
            cmd_parts = shlex.split(command, posix=False)  # Use posix=False for Windows compatibility
            process = subprocess.Popen(cmd_parts, shell=True) #Use shell=True for Windows to handle commands correctly
        else:
            cmd_parts = shlex.split(command)
            process = subprocess.Popen(cmd_parts)
        
        self.cmd_processes[title] = process
    
    #Terminate a running terminal command
    def stop_terminal_command(self, title):
        process = self.cmd_processes[title]

        #Check if the process is still running and terminate it
        if process and process.poll() is None:
            system = platform.system()
            if system == 'Windows':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], check=True)
            else:
                process.kill()
    
    #Handle button click for starting/stopping terminal commands
    def cmd_button_clicked(self, title, command):
        if self.cmd_running_state[title]:
            # If the command is running, stop it
            self.stop_terminal_command(title)

            cmd_button = self.cmd_buttons[title]
            cmd_button.setText(f'Start {title}')
            cmd_button.setStyleSheet("background-color: green;")

            self.cmd_running_state[title] = False
        else:
            # If the command is not running, start it
            self.run_terminal_command(title, command)

            cmd_button = self.cmd_buttons[title]
            cmd_button.setText(f'Stop {title}')
            cmd_button.setStyleSheet("background-color: red;")

            self.cmd_running_state[title] = True
        
    # Add a button that runs a terminal command on click
    def add_command_button(self, title, command):
        # Determine position in the grid layout
        row = self.plot_count // self.plots_per_row
        col = self.plot_count % self.plots_per_row
        self.plot_count += 1

        # Vertical layout to hold the plot and button
        container = QtWidgets.QVBoxLayout()

        # Create button
        cmd_button = QtWidgets.QPushButton(f'Start {title}')
        cmd_button.setStyleSheet(f"background-color: green;")
        cmd_button.clicked.connect(lambda _, cmd=command, t=title: self.cmd_button_clicked(t, cmd))
        self.cmd_buttons[title] = cmd_button

        # Add button to vertical container
        container.addWidget(cmd_button)

        # Wrap the layout in a QWidget and add it to the grid
        container_widget = QtWidgets.QWidget()
        container_widget.setLayout(container)
        self.grid_layout.addWidget(container_widget, row, col)

        # Mark the command as not running
        self.cmd_running_state[title] = False
    
    # Check the status of all command processes and update button states
    def check_command_status(self):
        for title in self.cmd_processes:
            process = self.cmd_processes[title]
            if process.poll() is not None:
                # Process has finished, update button state
                cmd_button = self.cmd_buttons[title]
                cmd_button.setText(f'Start {title}')
                cmd_button.setStyleSheet("background-color: green;")
                self.cmd_running_state[title] = False
    
    def cmd_timer(self, interval_ms):
        # Create a timer to check command status on a regular interval
        timer = QtCore.QTimer()
        timer.timeout.connect(lambda: self.check_command_status())
        timer.start(interval_ms)
        self.interval_timers['cmd_timer'] = timer #Store primarily to prevent garbage collection

    # Show the window and start the event loop
    def run(self):
        self.main_window.show()
        sys.exit(self.app.exec_())

# Example usage
if __name__ == '__main__':
    plotter = LivePlotter("Test Live Plotter", plots_per_row=2)

    # Add plots with data update intervals
    plotter.add_plot(title='Vessel Pressure', x_axis=('Time', 's'), y_axis=('Pressure', 'Pa'), buffer_size=100, csv_filepath='40L_run_control\pressure_log_copy.csv', datatype='pressure')
    plotter.start_timer(title='Vessel Pressure', interval_ms=1000)

    plotter.add_plot(title='Vessel Pressure 2', x_axis=('Time', 's'), y_axis=('Pressure', 'Pa'), buffer_size=100, csv_filepath='40L_run_control\pressure_log_copy_2.csv', datatype='pressure')
    plotter.start_timer(title='Vessel Pressure 2', interval_ms=1000)

    plotter.add_command_button(title='timeout 1', command='timeout /T 10')
    plotter.add_command_button('dir2', 'dir', 'dir')

    plotter.cmd_timer(500)  # Start the command status checking timer


    # Launch the application
    plotter.run()