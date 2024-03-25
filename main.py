"""
The lapd-plasma-analysis repository was written by Leo Murphy based on code
written in MATLAB by Conor Perks (MIT) and using the PlasmaPy and bapsflib libraries.
Comments are added inline. A separate documentation page is not yet complete.
"""

from helper import *
from file_access import ask_yes_or_no
from load_datasets import setup_datasets
from plots import multiplot_line_diagnostic, plot_line_diagnostic, plot_parallel_diagnostic

import matplotlib

""" End directory paths with a slash """
# hdf5_folder = "/Users/leomurphy/lapd-data/April_2018/"
# hdf5_folder = "/Users/leomurphy/lapd-data/March_2022/"
# hdf5_folder = "/Users/leomurphy/lapd-data/November_2022/"
# hdf5_folder = "/Users/leomurphy/lapd-data/January_2024/January_2024_all_working/"
hdf5_folder = "/Users/leomurphy/lapd-data/all_lang_nc/"

langmuir_nc_folder = hdf5_folder + ("lang_nc/" if hdf5_folder.endswith("/") else "/lang_nc/")

""" Set to False or equivalent if interferometry calibration is not desired """
interferometry_folder = False                               # TODO set to False to avoid interferometry calibration
# interferometry_folder = hdf5_folder
# interferometry_folder = "/Users/leomurphy/lapd-data/November_2022/uwave_288_GHz_waveforms/"

""" User parameters """
# TODO isweep_choice is user choice for probe or linear combination to use; see isweep_selector in helper.py for more
isweep_choice = [[1, 0, 0, 0], [0, 0, 1, 0]]
# isweep_choice = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
# isweep_choice = [[1, 0], [0, 1]]
# isweep_choice = [0]
bimaxwellian = False                                        # TODO perform both and store in same NetCDF file?
core_radius = 26. * u.cm                                    # From MATLAB code

# Diagram of LAPD
"""
       <- ~18m plasma length -> 
  ____________________________________       
  |    |                      '      |       A       
  |    |                      '      |       |   ~75 cm plasma diameter
  |____|______________________'______|       V
      (a)                    (b)    (c)
        +z direction (+ports) ==>
                  plasma flow ==>
            magnetic field B0 ==>

a) LaB6 electron beam cathode
b) downstream mesh anode
c) downstream cathode
"""

if __name__ == "__main__":

    # TODO list of hardcoded parameters
    #    (16, 24) for January_2024 steady state period (detect_steady_state_period in diagnostics.py)

    datasets, steady_state_plateaus_runs, diagnostic_name_dict, diagnostics_to_plot_list = setup_datasets(
        langmuir_nc_folder, hdf5_folder, interferometry_folder, isweep_choice, bimaxwellian)
    print("Diagnostics selected:", diagnostics_to_plot_list)

    # Plot chosen diagnostics for each individual dataset
    if ask_yes_or_no("Generate contour plot of selected diagnostics over time and radial position? (y/n) "):
        for plot_diagnostic in diagnostics_to_plot_list:
            for i in range(len(datasets)):
                plot_line_diagnostic(isweep_selector(datasets[i], isweep_choice), plot_diagnostic, 'contour',
                                     steady_state_plateaus_runs[i])

    # Plot radial profiles of diagnostic (steady-state time average), with color corresponding to first attribute
    #    and plot position on multiplot corresponding to second attribute
    if ask_yes_or_no("Generate line plot of selected diagnostics over radial position? (y/n) "):
        for plot_diagnostic in diagnostics_to_plot_list:
            multiplot_line_diagnostic(datasets, plot_diagnostic, isweep_choice, 'x',
                                      steady_state_by_runs=steady_state_plateaus_runs,
                                      core_rad=core_radius)

    if ask_yes_or_no("Generate line plot of selected diagnostics over time? (y/n) "):
        for plot_diagnostic in diagnostics_to_plot_list:
            multiplot_line_diagnostic(datasets, plot_diagnostic, isweep_choice, 'time',
                                      steady_state_by_runs=steady_state_plateaus_runs,
                                      core_rad=core_radius)

    datasets = sorted(datasets, key=lambda ds: ds.attrs['Exp name'])
    # Split two steady state periods for jan_2024 data: (16, 24) and (27, 33) and plot with dotted
    datasets_split = datasets.copy()
    steady_state_plateaus_runs_split = steady_state_plateaus_runs.copy()
    linestyles_split = ["solid"] * len(datasets)
    for i in range(len(datasets)):
        if datasets[i].attrs['Exp name'] == "January_2024":
            datasets_split += [datasets[i]]
            steady_state_plateaus_runs_split += [(27, 33)]
            linestyles_split += ["dotted"]

    # isweep_choice_center = [2 if dataset.attrs['Exp name'] == "January_2024" else 0 for dataset in datasets]
    isweep_choice_center_split = [2 if dataset.attrs['Exp name'] == "January_2024" else 0 for dataset in datasets_split]


    # Plot pressure versus z position for many datasets
    if ask_yes_or_no("Generate parallel pressure plot? (y/n) "):
        plot_parallel_diagnostic(datasets_split, steady_state_plateaus_runs_split, isweep_choice_center_split,
                                 linestyles_split, diagnostic="P_e")

    if ask_yes_or_no("Generate parallel electron temperature plot? (y/n) "):
        plot_parallel_diagnostic(datasets_split, steady_state_plateaus_runs_split, isweep_choice_center_split,
                                 linestyles_split, diagnostic="T_e", operation="median")

    if ask_yes_or_no("Generate parallel electron density plot? (y/n) "):
        plot_parallel_diagnostic(datasets_split, steady_state_plateaus_runs_split, isweep_choice_center_split,
                                 linestyles_split, diagnostic="n_e")

    if ask_yes_or_no("Generate parallel ion density plot? (y/n) "):
        plot_parallel_diagnostic(datasets_split, steady_state_plateaus_runs_split, isweep_choice_center_split,
                                 linestyles_split, diagnostic="n_i_OML")

    if ask_yes_or_no("Generate parallel electron-ion collision frequency plot? (y/n) "):
        plot_parallel_diagnostic(datasets_split, steady_state_plateaus_runs_split, isweep_choice_center_split,
                                 linestyles_split, diagnostic="nu_ei")


    if ask_yes_or_no("Generate scatter plot of first two selected diagnostics? (y/n) "):
        diagnostics_points = []
        marker_styles = ['o' if style == 'solid' else 'x' for style in linestyles_split]
        color_map = matplotlib.colormaps["plasma"](np.linspace(0, 0.9, len(datasets)))

        plt.rcParams['figure.figsize'] = (5, 3.5)
        plt.rcParams['figure.dpi'] = 300

        for i in range(len(datasets_split)):
            diagnostics_point = []
            for plot_diagnostic in diagnostics_to_plot_list[:2]:
                diagnostic_mean = core_steady_state(
                    datasets_split[i][plot_diagnostic], core_radius, steady_state_plateaus_runs_split[i], "mean",
                    dims_to_keep=("isweep",))
                diagnostics_point += [diagnostic_mean[{"isweep": isweep_choice_center_split[i]}].item()]
            diagnostics_points += [diagnostics_point]

        scatter_points = np.array(diagnostics_points)
        dataset_names = np.unique([dataset.attrs['Run name'] for dataset in datasets])
        for i in range(len(scatter_points)):
            plt.scatter(scatter_points[i, 0], scatter_points[i, 1], marker=marker_styles[i],
                        color=color_map[dataset_names == datasets_split[i].attrs['Run name']])
            plt.annotate(f"{datasets_split[i].attrs['Exp name'][:3]}, #{datasets_split[i].attrs['Run name'][:2]}",
                         (scatter_points[i, 0], scatter_points[i, 1]), size="x-small")  # noqa
        plt.xlabel(diagnostics_to_plot_list[0])
        plt.ylabel(diagnostics_to_plot_list[1])
        plt.title("Scatter plot for selected runs at port ~27-29"
                  "\nJan 2024 runs: x marker = 2nd steady-state")
        plt.tight_layout()
        plt.show()


    # (UNFINISHED) Shot plot: multiplot line diagnostics at specific time, with x-axis = x pos and curve color = shot #
    """if ask_yes_or_no("Generate line shot plot of selected diagnostics over radial position? (y/n) "):
        for plot_diagnostic in diagnostic_to_plot_list:
            multiplot_line_diagnostic(datasets, plot_diagnostic, isweep_choice, steady_state_plateaus_runs,
                                      tolerance=plot_tolerance)
    """

# TODO Not all MATLAB code has been transferred (e.g. neutrals, ExB)
# QUESTION: can we calibrate both Langmuir probes using an interferometry ratio depending only on one of them?
