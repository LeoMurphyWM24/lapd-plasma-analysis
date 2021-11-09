"""
The lapd-plasma-analysis repository was written by Leo Murphy based on code 
written in MATLAB by Conor Perks (MIT) and using the PlasmaPy online code library.
Comments are added inline. A separate documentation page is not yet complete.
"""
from getIVsweep import *
from characterization import *
from diagnostics import *
from plots import *
from netCDFaccess import *
from interferometry import *
from neutrals import *
from setup import *

# User global parameters
sample_sec = (100 / 16 * 1e6) ** (-1) * u.s                   # Note that this is small. 10^6 is in the denominator
probe_area = (1. * u.mm) ** 2                                 # From MATLAB code
core_region = 26. * u.cm                                      # From MATLAB code
ion_type = 'He-4+'
bimaxwellian = False
smoothing_margin = 0
steady_state_start_plateau, steady_state_end_plateau = 5, 11  # From MATLAB code
# End of global parameters

# User file path names
hdf5_path = "/Users/REPLACE-THIS-PATH.hdf5"   # Link to the HDF5 files, available on the GitHub repository Releases page 
interferometry_filename = hdf5_path           # interferometry data stored in same HDF5 file
save_diagnostic_name = "diagnostic_dataset"  # Note: file is saved to a subfolder “netcdf” to be created if necessary
open_diagnostic_name = save_diagnostic_name   # write to and read from the same location
netcdf_subfolder_name = "netcdf"              # subfolder to save and read netcdf files; set to “” to use current folder
# End of file path names

# User file options
""" Set the below variable to True to open an existing diagnostic dataset from a NetCDF file
    or False to create a new diagnostic dataset from the given HDF5 file. """
use_existing = True
""" Set the below variable to True to save diagnostic data to a NetCDF file if a new one is created from HDF5 data. """
save_diagnostics = True
# End of file options


# Establish paths to create files in specified netcdf subfolder
netcdf_subfolder_path = ensure_netcdf_directory(netcdf_subfolder_name)
save_diagnostic_path = netcdf_path(save_diagnostic_name, netcdf_subfolder_path, bimaxwellian)
open_diagnostic_path = netcdf_path(open_diagnostic_name, netcdf_subfolder_path, bimaxwellian)

# Read experimental parameters
experimental_parameters, experimental_parameters_rounded = setup_lapd(hdf5_path)
print("Experimental parameters:", {key: str(value) for key, value in experimental_parameters_rounded.items()})
bias, current, x, y = get_isweep_vsweep(hdf5_path)

# Create the diagnostics dataset by generating new or opening from a NetCDF file
diagnostics_dataset = read_netcdf(open_diagnostic_path) if use_existing else None  # desired dataset or None to use HDF5
if not diagnostics_dataset:  # diagnostic dataset not loaded; create new from HDF5 file
    characteristics = characterize_sweep_array(bias, current, x, y, margin=smoothing_margin, sample_sec=sample_sec)
    diagnostics_dataset = plasma_diagnostics(characteristics, probe_area, ion_type, bimaxwellian=bimaxwellian)
    if save_diagnostics:
        write_netcdf(diagnostics_dataset, save_diagnostic_path)

print("Plasma diagnostics:", [key for key in diagnostics_dataset.keys()])

# Contour plot of electron temperature
radial_diagnostic_plot(diagnostics_dataset, diagnostic='T_e', plot='contour')

# Uncomment this section to perform analysis of a single sample Isweep-Vsweep curve
"""
sample_indices = (30, 0, 7)  # x position, y position, plateau number within frame
sample_plateau = characteristics[sample_indices].item()
print(swept_probe_analysis(sample_plateau, probe_area, ion_type,
                           visualize=True, plot_EEDF=True, bimaxwellian=bimaxwellian))
plt.show()
"""
"""
print({diagnostic: diagnostics_dataset[diagnostic][sample_indices].values for diagnostic in diagnostics_dataset.keys()})
print("Done analyzing sample characteristic")
"""

# Note: in the future, this will consider only the steady-state region
if not bimaxwellian:
    pressure = (3 / 2) * diagnostics_dataset['n_e'] * diagnostics_dataset['T_e'] * (1. * u.eV * u.m ** -3).to(u.Pa)
    both = xr.ufuncs.logical_and
    plateau = pressure.coords['plateau']  # rename variables for comprehensibility

    steady_state_pressure = pressure.where(both(plateau >= steady_state_start_plateau, plateau <= steady_state_end_plateau))
    steady_state_pressure.squeeze(dim='y').assign_attrs({"units": str(u.Pa)}).plot.contourf(x='time', y='x', robust=True)
    plt.title("Steady state pressure")
    plt.show()
else:
    print("Pressure plotting not yet supported for bimaxwellian temperature distributions.")

electron_density, density_scaling = interferometry_calibration(
    diagnostics_dataset['n_e'], interferometry_filename,
    steady_state_start_plateau, steady_state_end_plateau, core_region=core_region)

# Plot electron density data that was calibrated using interferometry data
electron_density.squeeze().plot.contourf(robust=True)
plt.show()

neutral_ratio(diagnostics_dataset['n_e'], experimental_parameters, steady_state_start_plateau, steady_state_end_plateau)

# Note: Plot generation code and neutral fraction analysis is incomplete.
# Note: The non-bimaxwellian electron temperature calculated using the PlasmaPy code seems to be 
#    the *reciprocal* of the correct value. I may raise an issue on the PlasmaPy GitHub page.