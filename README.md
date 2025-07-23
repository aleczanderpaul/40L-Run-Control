# 40L-Run-Control

Repository of code for a run control program for the 40L TPC. Intended to measure/plot vessel pressure and VMM temperature in real time, and to control the experiment remotely.

## launch_GUI.py

A script to launch the run control GUI. The widgets (plots, buttons, etc.) to display can be specified in the file using functions in the LivePlotter class (from core_tools/gui/live_plotter_GUI_class.py). Some notes about how to use launch_GUI.py are left as comments inside the file.

## log_pressure.py

A script that connects to an MKS PDR 2000 (pressure sensor that uses RS-232 Serial protocol) and writes the pressure to a CSV file at a specified interval indefinitely or for a limited duration.

To run script, use format: python3 <log_pressure.py filepath> <log_filepath (make sure to add .csv)> <serial_port> <interval_sec> <duration_sec (optional, leave empty for indefinite)>

If using venv, use format: .venv\Scripts\python.exe <log_pressure.py filepath> <log_filepath (make sure to add .csv)> <serial_port> <interval_sec> <duration_sec (optional, leave empty for indefinite)>

While technically the user can create the CSV file manually and the script will skip making one if it already exists, it is highly recommended that the user lets the script make the file, as it will make the headers for each column correctly for the GUI to read from.

## log_temperature.py

TO BE DEVELOPED

## LivePlotter class

This class uses dictionaries to store and sort data, so titles are a very important concept for this class. Every widget has a title specified by the user and can be any string, but must be unique across all widgets. The title lets the GUI know where to store important processes for the widgets (e.g., plot data, timers, filepaths, etc.) so that each one can run independently, and can be accessed later.

All the functions inside the class are explained below, but the only ones that should be called in launch_GUI.py are add_plot, start_timer, add_command_button, cmd_timer, and run.

Source code is located at core_tools/gui/live_plotter_GUI_class.py.

### add_plot(title, x_axis, y_axis, buffer_size, csv_filepath, datatype)

Adds a plot to the window and a button that will start/stop automatic updates to the plot. Data is pulled from a CSV file, so the CSV must exist before this function is called, even if it is empty. It is highly recommended to use log_pressure.py and log_temperature.py to create the CSV's, not manually.

x_axis and y_axis are tuples of format (label, unit). For example, x_axis = ('Time', 's') means the x-axis label is Time, and the units are s (seconds). pyqtgraph handles metric prefixes automatically, so there is no need to refactor all your data to be in ms, the program will plot in units that are "smart" to plot in.

buffer_size is an int and represents the number of data points the plot will display at a single time. This is to save memory and to not be an eyesore, so don't set this number egregiously high.

csv_filepath is a string of the filepath to the CSV the plot will pull data from.

datatype is a string that tells the GUI what is being plotted so it knows how to get the relevant x and y data. For example, datatype='pressure' tells the GUI to plot pressure from the MKS PDR 2000 vs how many seconds ago the data was taken. The current supported datatypes are found in core_tools/gui/get_data_for_GUI.py inside the get_n_XY_datapoints function.

### update(title)

Fetches the data from the CSV and updates the plot accordingly. If there is less data in the CSV than the buffer size of the plot, it will plot what is available. If there is more data in the CSV than the buffer size, it will plot data only from the bottom rows of the CSV up to the buffer size. This function is usually fired on a timer so that the plots update constantly (see below sections for more information).

### get_elapsed_time(title)

Return elapsed time in seconds since the plot has started. Using the start/stop button associated with the plot will reset this timer.

### start_timer(title, interval_ms)

Starts the interval timer to drive plot updates and the elapsed timer. Run this line after each add_plot function call, otherwise the plot will never be updated.

interval_ms is an int that specifies the length of the interval timer that calls the update function.

### toggle_plot(title, buffer_size)

Handles the start/stop button for each plot. Changes color, text, and state of the timers when button is pressed.

### run_terminal_command(title, command)

Runs a command in the terminal, to be used in conjunction with a button. Works for both Linux and Windows.

command is a string of the command to be run.

### stop_terminal_command(title)

Terminates a running command, to be used in conjunction with a button. Works for both Linux and Windows.

### cmd_button_clicked(title, command)

Similar to toggle_plot, but handles the buttons that execute terminal commands instead of starting/stopping plot updates.

### add_command_button(title, command)

Adds a button that runs a terminal command on click.

command is a string of the command to be run.

### check_command_status()

Checks the status of all terminal processes associated with a button and reverts the button(s) back to their original state if the process is resolved.

### cmd_timer(interval_ms)

Creates an interval timer that calls check_command_status. This function should be called once after all the command buttons have been added to the window.

interval_ms is an int that specifies the length of the interval timer that calls the check_command_status function.

### cleanup()

Terminates all the running subprocesses the GUI started (e.g., logging pressure script). Is called when the user exits the GUI.

### run()

Shows the window and starts the event loop. Call this after all the widgets have been added to the window.
