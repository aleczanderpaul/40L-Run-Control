from core_tools.gui.live_plotter_GUI_class import LivePlotter
from core_tools.pressure.save_pressure_readings_functions import create_pressure_log_csv

'''Launches run control GUI for the 40L system as specified by the user in this file.'''
#Create the CSV files for logging data BEFORE adding the relevant plot to the GUI window because the plotter will look for the file when it is created. Use the create_X_log_csv functions to create the files.
#Do NOT use any filenames with whitespaces in them, as this will cause issues with the terminal command buttons.
#The widgets (plots, buttons, etc.) are added to the GUI window in the order they are written here and fill from left to right, top to bottom.
#For more infromation on how to use the LivePlotter class, see GitHub readme file or the source code at core_tools/gui/live_plotter_GUI_class.py

plotter = LivePlotter("Test Live Plotter", plots_per_row=1)

pressure_log_filepath = '40L_run_control/pressure_log_07_23_25.csv'
create_pressure_log_csv(pressure_log_filepath)
plotter.add_plot(title='Plot Vessel Pressure', x_axis=('Time since present', 's'), y_axis=('Pressure', 'Torr'), buffer_size=100, csv_filepath=pressure_log_filepath, datatype='pressure')
plotter.start_timer(title='Plot Vessel Pressure', interval_ms=1000)

plotter.add_command_button(title='Log Vessel Pressure', command=f'.venv\Scripts\python.exe 40L_run_control/log_pressure.py {pressure_log_filepath} COM4 2')
plotter.cmd_timer(500)

plotter.run()