import numpy as np
import xarray as xr
import astropy.units as u

from langmuir.helper import crunch_data, ion_temperature
from plasmapy.particles import particle_mass


def get_mach_numbers(mach_isat_da: xr.DataArray):
    r"""
    Returns Dataset of Mach numbers at each position and time increment.
    Dimensions are (probe, face, x, y, shot, time).
    Note that Mach probes have much higher time resolution than the Langmuir measurement frequency.

    Mathematics
    ----------

    By C. Perks and by "Mach probes" (Chung 2012), the parallel Mach number :math:`M_z` is given by

    .. math::
        M_z = M_c \ln(R_1)
    where :math:`M_c` is a magnetization factor :math:`= 1/K` in Chung 2012,
    and :math:`R_1` is the ratio of upstream ion saturation current to downstream ion saturation current.

    By the same sources, using a Gundestrup probe that measures the ion saturation current in multiple directions,
    the perpendicular Mach number :math:`M_\perp` may be calculated as

    .. math::
        M_\perp = M_c \ln(R_1 / R_2) / \cot(\alpha) \\

        \ \ \ \ \ \ = (M_c \ln(R_1)  - M_c \ln(R_2)) \cdot \tan(\alpha)

        \ \ \ \ \ \ = (M_z - M_c \ln(R_2)) \cdot \tan(\alpha)
    where :math:`R_2` is the ratio of more-upstream ion saturation current to more-downstream ion saturation current
    for probe faces lying along an axis at an angle :math:`\alpha` from perpendicular to the flow;
    for example, :math:`\alpha = \pi/2` for a perfect upstream-downstream probe face alignment.
    This model is valid when :math:`\pi/6 < \alpha < 5 \pi/6`.

    In this function, the perpendicular Mach number is found as the average of two estimates for :math:`M_\perp`
    based on probe face axis alignment offsets of :math:`\pi/4` and :math:`3\pi/4` from horizontal.

    Parameters
    ----------
    :param mach_isat_da:
    :return:
    """

    """

        Model of Mach probe faces (perfect octagon)
                            ___________
                 |         /           \ 
        fore     |    3  /               \  4
                 |      |                 |
    (<- Cathode) |   2  |                 |  5            <----  B-field
                 |      |                 |
        aft      |    1  \               /  6
                 |         \___________/ 

    """  # noqa

    """diagnostics_ds = xr.Dataset({key: xr.DataArray(data=templates[key],
                                                   dims=['probe', 'face', 'x', 'y', 'shot', 'time'],
                                                   coords=(('probe', np.arange(num_probe)),
                                                           ('face', faces),
                                                           ('x', x, {"units": str(u.cm)}),
                                                           ('y', y, {"units": str(u.cm)}),
                                                           ('shot', np.arange(num_shots)),
                                                           ('time', ramp_times.to(u.ms).value, {"units": str(u.ms)}))
                                                   ).assign_coords({'plateau': ('time', np.arange(num_plateaus) + 1),
                                                                    'port': ('probe', ports),
                                                                    'z':    ('probe', port_zs, {"units": str(u.cm)})}
                                                                   ).assign_attrs({"units": keys_units[key]})
                                 for key in keys_units.keys()})"""

    """CONSTANTS AND DESCRIPTIONS ARE TAKEN FROM MATLAB CODE WRITTEN BY CONOR PERKS"""
    # Mach probe calculation constants
    magnetization_factor = 0.5  # Mag. factor value from Hutchinson's derivation incorporating diamagnetic drift
    angle_fore = np.pi / 4 * u.rad  # [rad] Angle the face in fore direction makes with B-field
    angle_aft = np.pi / 4 * u.rad  # [rad] Angle the face in aft direction makes with B-field

    print("Calculating Mach numbers...")

    """Parallel Mach number"""
    parallel_mach = magnetization_factor * np.log(
        mach_isat_da.sel(face=2) / mach_isat_da.sel(face=5))  # .sortby("probe")
    # print(" * Parallel Mach number found ")

    mach_ds = xr.Dataset({"M_para": parallel_mach})  # "Parallel Mach number"

    """Perpendicular Mach number"""
    if np.isin(np.array([1, 3, 4, 6]), mach_isat_da.face).all():
        mach_correction_fore = magnetization_factor * np.log(mach_isat_da.sel(face=3) / mach_isat_da.sel(face=6))
        mach_correction_aft = magnetization_factor * np.log(mach_isat_da.sel(face=1) / mach_isat_da.sel(face=4))

        perpendicular_mach_fore = (parallel_mach - mach_correction_fore) * np.cos(angle_fore)
        perpendicular_mach_aft = (parallel_mach - mach_correction_aft) * np.cos(angle_aft)
        perpendicular_mach = xr.concat([perpendicular_mach_fore, perpendicular_mach_aft], 'location').mean('location')
        # print(" * Perpendicular Mach number found ")

        mach_ds = mach_ds.assign({"M_perp":      perpendicular_mach,            # "Perpendicular Mach number"
                                  "M_perp_fore": perpendicular_mach_fore,       # "Perpendicular fore Mach number"
                                  "M_perp_aft":  perpendicular_mach_aft})       # "Perpendicular aft Mach number"

    return mach_ds


def get_velocity(mach_ds: xr.Dataset, electron_temperature_da: xr.DataArray, ion_type: str):
    r"""
    Returns Dataset of flow velocity at each position and time.
    Dimensions are (probe, face, x, y, shot, time (matching Langmuir plateaus))

    Mathematics
    ----------
    From MATLAB code by C. Perks:
    "Note that :math:`M=v/C_s` where :math:`C_s = \sqrt{(T_e+T_i)/M_i}`, but we will assume that :math:`T_i \sim 1` eV".
    A supporting 1 eV estimate for LAPD ion temperature was found on the LAPD BAPSF website.

    Parameters
    ----------
    :param mach_ds:
    :param electron_temperature_da:
    :param ion_type:
    :return:
    """

    """
    Electron temperature DataArray will have dimensions
        probe               (additional coordinates: port, z),
        face, x, y, shot,
        time                (additional coordinates: plateau (1-based))
    """

    ion_mass = particle_mass(ion_type)
    ion_adiabatic_index = 3
    velocity_unit = u.m / u.s

    sound_speed = np.sqrt((electron_temperature_da + ion_adiabatic_index * ion_temperature.to(u.eV).value) / ion_mass)  # .sortby("probe")
    sound_speed *= np.sqrt(1 * u.eV / u.kg).to(velocity_unit).value  # convert speed from sqrt(eV/kg) to [velocity unit]

    crunched_mach_ds = crunch_data(mach_ds, "time", sound_speed.coords['time'])
    crunched_mach_ds.coords['time'] = sound_speed.coords['time']  # Ensure time has units in new dataset
    # Below: reindex Mach probe data according to nearest Langmuir probe in electron density dataset
    crunched_mach_ds = crunched_mach_ds.swap_dims({"probe": "port"}).reindex_like(
        sound_speed.swap_dims({"probe": "port"}), method="nearest", tolerance=3
    ).swap_dims({"port": "probe"})

    # print(" * Generating parallel velocity profiles...")
    parallel_velocity = crunched_mach_ds['M_para'] * sound_speed            # "Parallel Mach number"
    parallel_velocity.attrs['units'] = str(velocity_unit)
    velocity = xr.Dataset({"v_para": parallel_velocity})                    # "Parallel velocity"

    if "M_perp" in crunched_mach_ds:                                        # "Perpendicular Mach number"
        # print(" * Generating perpendicular velocity profiles...")
        perpendicular_velocity = crunched_mach_ds['M_perp'] * sound_speed   # "Perpendicular Mach number"
        perpendicular_velocity.attrs['units'] = str(velocity_unit)
        velocity = velocity.assign({"v_perp": perpendicular_velocity})      # Perpendicular velocity

    return velocity
