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

        self.tab_objects = {}  # tab_name -> LiveTab object

        #Calls the clanup function when the application is about to quit so that all running subprocesses are terminated
        self.app.aboutToQuit.connect(self.cleanup)

    #Create a tab in the window to put plots and buttons in
    def create_tab(self, tab_name, plots_per_row):
        tab = LiveTab(plots_per_row)
        self.tab_objects[tab_name] = tab
        self.tabs.addTab(tab, tab_name)
        return tab

    #Call cleanup function for each tab to end all running subprocesses
    def cleanup(self):
        for tab_name in self.tab_objects:
            self.tab_objects[tab_name].cleanup()
    
    # Show the window and start the event loop
    def run(self):
        self.main_window.show()
        sys.exit(self.app.exec_())

class LiveTab(QtWidgets.QWidget):
    def __init__(self, plots_per_row):
        super().__init__() # Call the constructor of the parent class (QWidget) to properly initialize the widget. This class is now a custom QTWidget

        self.layout = QtWidgets.QGridLayout() ## Create a grid layout manager to arrange child widgets (plots, buttons) in a grid format.
        self.setLayout(self.layout)

        self.plots_per_row = plots_per_row
        self.plot_counts = 0

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
        self.cmd_command_strings = {}             # title -> command string (useful if we want to change command on the fly)

        #Internal state tracking for dropdown menus
        self.dd_menus = {}                        # title ->
        self.dd_option_names = {}                 # title ->
        self.dd_option_values = {}                 # title ->
    
    # Add a new plot with button below it
    def add_plot(self, title, x_axis, y_axis, buffer_size, csv_filepath, datatype): #x_axis and y_axis are tuples of (label, unit), and buffer_size is the number of data points to display at once
        index = self.plot_counts
        plots_per_row = self.plots_per_row
        self.plot_counts += 1
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
        start_stop_button.clicked.connect(lambda _, t=title: self.toggle_plot(t))
        self.start_stop_buttons[title] = start_stop_button

        # Add plot and button to vertical container
        container.addWidget(plot_widget)
        container.addWidget(start_stop_button)

        # Wrap the layout in a QWidget and add it to the grid
        container_widget = QtWidgets.QWidget()
        container_widget.setLayout(container)
        self.layout.addWidget(container_widget, row, col)

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
    def toggle_plot(self, title):
        if self.running_state[title]:
            # Stop the timer and update the button text
            self.interval_timers[title].stop()
            self.start_stop_buttons[title].setText(f"Start {title}")
            self.start_stop_buttons[title].setStyleSheet("background-color: green;")
            self.running_state[title] = False
        else:
            # Reset data and timer, restart updates
            buffer_size = self.data[title]["buffer_size"]
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
    def cmd_button_clicked(self, title):
        command = self.cmd_command_strings[title] #this method allows us to dynamically change the command if necessary
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
        index = self.plot_counts
        plots_per_row = self.plots_per_row
        self.plot_counts += 1
        row = index // plots_per_row
        col = index % plots_per_row

        # Vertical layout to hold the plot and button
        container = QtWidgets.QVBoxLayout()

        # Create button
        cmd_button = QtWidgets.QPushButton(f'Start {title}')
        cmd_button.setStyleSheet(f"background-color: green;")
        self.cmd_command_strings[title] = command
        cmd_button.clicked.connect(lambda _, t=title: self.cmd_button_clicked(t))
        self.cmd_buttons[title] = cmd_button

        # Add button to vertical container
        container.addWidget(cmd_button)

        # Wrap the layout in a QWidget and add it to the grid
        container_widget = QtWidgets.QWidget()
        container_widget.setLayout(container)
        self.layout.addWidget(container_widget, row, col)

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
    
    #Add a dropdown menu with specified options and values attached to the options
    def add_dropdown_menu(self, title, option_names, option_values, cmd_button_title=None, on_change_callback=None):
        index = self.plot_counts
        plots_per_row = self.plots_per_row
        self.plot_counts += 1
        row = index // plots_per_row
        col = index % plots_per_row

        # Vertical layout to hold the plot and button
        container = QtWidgets.QVBoxLayout()

        # Label
        label = QtWidgets.QLabel(title)
        container.addWidget(label)

        # Dropdown (QComboBox)
        dropdown_box = QtWidgets.QComboBox()
        for i in range(len(option_names)):
            dropdown_box.addItem(option_names[i], userData=option_values[i])
        self.dd_menus[title] = dropdown_box
        self.dd_option_names[title] = option_names
        self.dd_option_values[title] = option_values

        # If a callback function is provided, connect it
        if on_change_callback and cmd_button_title:
            dropdown_box.currentIndexChanged.connect(
                lambda idx, t=title, cmd_t=cmd_button_title: on_change_callback(t, cmd_t, dropdown_box.itemText(idx), dropdown_box.itemData(idx))
            )
        elif on_change_callback and not cmd_button_title:
            dropdown_box.currentIndexChanged.connect(
                lambda idx, t=title: on_change_callback(t, dropdown_box.itemText(idx), dropdown_box.itemData(idx))
            )

        # Add button to vertical container
        container.addWidget(dropdown_box)

        # Wrap the layout in a QWidget and add it to the grid
        container_widget = QtWidgets.QWidget()
        container_widget.setLayout(container)
        container_widget.setMaximumWidth(500) #prevent stretching (aesthetics)
        self.layout.addWidget(container_widget, row, col)

    #Changes the command string associated with a specified command button based on the title of the button
    def change_cmd_button_command(self, title, new_command):
        self.cmd_command_strings[title] = new_command
    
    #Specialized function specifically for the 40L TPC log pressure command, will likely not be useful for a general user of this program
    #People using this program for a different use case will need to edit this function and/or write a new one to do the editing they need to the command string
    def change_pressure_log_cmd(self, title, cmd_button_title, dropdown_text, new_option_value):
        old_command = self.cmd_command_strings[cmd_button_title]

        parts = old_command.split()
        parts[-1] = str(new_option_value)

        new_command = ' '.join(parts)

        print(f'New Pressure Logging Command: {new_command}') #for debugging

        self.change_cmd_button_command(cmd_button_title, new_command)

    
    # End all running subprocesses
    def cleanup(self):
        for title in self.cmd_processes:
            process = self.cmd_processes[title]
            if process.poll() is None:
                self.stop_terminal_command(title)
        

# Example usage
if __name__ == '__main__':
    plotter = LivePlotter("Test Live Plotter")

    pressure_log_filepath = '40L_run_control/pressure_log_07_23_25.csv'

    #create_pressure_log_csv(pressure_log_filepath) this file doesnt see create_pressure_log function, but launch_GUI.py does

    pressure_tab = plotter.create_tab(tab_name='Pressure', plots_per_row=1)
    temp_tab = plotter.create_tab(tab_name='Temperature', plots_per_row=4)

    pressure_tab.add_plot(title='Plot Vessel Pressure', x_axis=('Time since present', 's'), y_axis=('Pressure', 'Torr'), buffer_size=100, csv_filepath=pressure_log_filepath, datatype='pressure')
    pressure_tab.start_timer(title='Plot Vessel Pressure', interval_ms=1000)

    pressure_tab.add_command_button(title='Log Vessel Pressure', command=f'.venv\Scripts\python.exe 40L_run_control/log_pressure.py {pressure_log_filepath} COM4 2')
    pressure_tab.add_command_button(title='test', command=f'timeout /T 10')
    pressure_tab.cmd_timer(500)

    temp_tab.add_plot(title='Plot VMM 1 Temperature', x_axis=('Time since present', 's'), y_axis=('Temperature', 'deg C'), buffer_size=100, csv_filepath=pressure_log_filepath, datatype='pressure')
    temp_tab.start_timer(title='Plot VMM 1 Temperature', interval_ms=1000)

    temp_tab.add_plot(title='Plot VMM 2 Temperature', x_axis=('Time since present', 's'), y_axis=('Temperature', 'deg C'), buffer_size=100, csv_filepath=pressure_log_filepath, datatype='pressure')
    temp_tab.start_timer(title='Plot VMM 2 Temperature', interval_ms=1000)

    temp_tab.add_plot(title='Plot VMM 3 Temperature', x_axis=('Time since present', 's'), y_axis=('Temperature', 'deg C'), buffer_size=100, csv_filepath=pressure_log_filepath, datatype='pressure')
    temp_tab.start_timer(title='Plot VMM 3 Temperature', interval_ms=1000)

    temp_tab.add_command_button(title='test', command=f'timeout /T 10')
    temp_tab.cmd_timer(500)

    plotter.run()