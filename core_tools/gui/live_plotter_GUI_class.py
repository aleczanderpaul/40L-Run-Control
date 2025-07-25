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
    def __init__(self, win_title):
        # Create the main Qt application
        self.app = QtWidgets.QApplication(sys.argv)

        # Main window setup
        self.main_window = QtWidgets.QMainWindow()
        self.main_widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)
        self.main_window.setCentralWidget(self.main_widget)
        self.main_window.setWindowTitle(win_title)

        # Add a tab widget to the main layout
        self.tabs = QtWidgets.QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # Keep track of layouts for each tab
        self.tab_layouts = {}  # tab_name -> QGridLayout
        self.tab_widgets = {}  # tab_name -> QWidget
        self.plot_counts = {}  # tab_name -> count of widgets added to that tab
        self.plots_per_row = {} #tab_name -> plots in each row allowed before moving to next

        # Internal state tracking for plots
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

        #Calls the clanup function when the application is about to quit so that all running subprocesses are terminated
        self.app.aboutToQuit.connect(self.cleanup)

    #Create a tab in the window to put plots and buttons in
    def create_tab(self, tab_name, plots_per_row):
        tab_widget = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout()
        tab_widget.setLayout(layout)
        self.tabs.addTab(tab_widget, tab_name)
        self.tab_layouts[tab_name] = layout
        self.tab_widgets[tab_name] = tab_widget
        self.plots_per_row[tab_name] = plots_per_row
        self.plot_counts[tab_name] = 0
    
    # Add a new plot with button below it
    def add_plot(self, title, x_axis, y_axis, buffer_size, csv_filepath, datatype, tab_name): #x_axis and y_axis are tuples of (label, unit), and buffer_size is the number of data points to display at once
        layout = self.tab_layouts[tab_name]
        index = self.plot_counts[tab_name]
        plots_per_row = self.plots_per_row[tab_name]
        self.plot_counts[tab_name] += 1
        row = index // plots_per_row
        col = index % plots_per_row

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
        layout.addWidget(container_widget, row, col)

    # Update function: fetches data from CSV and updates the plot
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
    def add_command_button(self, title, command, tab_name):
        layout = self.tab_layouts[tab_name]
        index = self.plot_counts[tab_name]
        plots_per_row = self.plots_per_row[tab_name]
        self.plot_counts[tab_name] += 1
        row = index // plots_per_row
        col = index % plots_per_row

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
        layout.addWidget(container_widget, row, col)

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
    
    # End all running subprocesses
    def cleanup(self):
        for title in self.cmd_processes:
            process = self.cmd_processes[title]
            if process.poll() is None:
                self.stop_terminal_command(title)

    # Show the window and start the event loop
    def run(self):
        self.main_window.show()
        sys.exit(self.app.exec_())

# Example usage
if __name__ == '__main__':
    plotter = LivePlotter("Test Live Plotter")

    pressure_log_filepath = '40L_run_control/pressure_log_07_23_25.csv'

    #create_pressure_log_csv(pressure_log_filepath) this file doesnt see create_pressure_log function, but launch_GUI.py does

    plotter.create_tab(tab_name='Pressure', plots_per_row=1)
    plotter.create_tab(tab_name='Temperature', plots_per_row=4)
    plotter.add_plot(title='Plot Vessel Pressure', x_axis=('Time since present', 's'), y_axis=('Pressure', 'Torr'), buffer_size=100, csv_filepath=pressure_log_filepath, datatype='pressure', tab_name='Pressure')
    plotter.start_timer(title='Plot Vessel Pressure', interval_ms=1000)

    plotter.add_plot(title='Plot VMM 1 Temperature', x_axis=('Time since present', 's'), y_axis=('Temperature', 'deg C'), buffer_size=100, csv_filepath=pressure_log_filepath, datatype='pressure', tab_name='Temperature')
    plotter.start_timer(title='Plot VMM 1 Temperature', interval_ms=1000)

    plotter.add_plot(title='Plot VMM 2 Temperature', x_axis=('Time since present', 's'), y_axis=('Temperature', 'deg C'), buffer_size=100, csv_filepath=pressure_log_filepath, datatype='pressure', tab_name='Temperature')
    plotter.start_timer(title='Plot VMM 2 Temperature', interval_ms=1000)

    plotter.add_plot(title='Plot VMM 3 Temperature', x_axis=('Time since present', 's'), y_axis=('Temperature', 'deg C'), buffer_size=100, csv_filepath=pressure_log_filepath, datatype='pressure', tab_name='Temperature')
    plotter.start_timer(title='Plot VMM 3 Temperature', interval_ms=1000)

    plotter.add_command_button(title='Log Vessel Pressure', command=f'.venv\Scripts\python.exe 40L_run_control/log_pressure.py {pressure_log_filepath} COM4 2', tab_name='Pressure')
    plotter.cmd_timer(500)

    plotter.run()