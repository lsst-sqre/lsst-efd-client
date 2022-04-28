"""Free functions to help out with EFD operations.
"""
from astropy.time import Time
import numpy
import pandas


def merge_packed_time_series(packed_dataframe, base_field, stride=1,
                             ref_timestamp_col="cRIO_timestamp", fmt='unix_tai',
                             scale='tai'):
    """Select fields that are time samples and unpack them into a dataframe.
    Parameters
    ----------
    packed_dataframe : `pandas.DataFrame`
        packed data frame containing the desired data
    base_field :  `str`
        Base field name that will be expanded to query all
        vector entries.
    stride : `int`, optional
        Only use every stride value when unpacking.  Must be a factor
        of the number of packed values.
        (1 by default)
    ref_timestamp_col : `str`, optional
        Name of the field name to use to assign timestamps to unpacked
        vector fields (default is 'cRIO_timestamp').
    fmt : `str`, optional
        Format to give to the `astropy.Time` constructor.  Defaults to
        'unix_tai' since most internal timestamp columns are in TAI.
    scale : `str`, optional
        Time scale to give to the `astropy.Time` constructor.  Defaults to
        'tai'.
    Returns
    -------
    result : `pandas.DataFrame`
        A `pandas.DataFrame` containing the results of the query.
    """

    packed_fields = [k for k in packed_dataframe.keys() if k.startswith(base_field)
                     and k[len(base_field):].isdigit()]
    packed_fields = sorted(packed_fields, key=lambda k: int(k[len(base_field):]))  # sort by pack ID
    npack = len(packed_fields)
    if npack % stride != 0:
        raise RuntimeError(f"Stride must be a factor of the number of packed fields: {stride} v. {npack}")
    packed_len = len(packed_dataframe)
    n_used = npack//stride   # number of raw fields being used
    output = numpy.empty(n_used * packed_len)
    times = numpy.empty_like(output, dtype=packed_dataframe[ref_timestamp_col][0])

    if packed_len == 1:
        dt = 0
    else:
        dt = (packed_dataframe[ref_timestamp_col][1] - packed_dataframe[ref_timestamp_col][0])/npack
    for i in range(0, npack, stride):
        i0 = i//stride
        output[i0::n_used] = packed_dataframe[f"{base_field}{i}"]
        times[i0::n_used] = packed_dataframe[ref_timestamp_col] + i*dt

    timestamps = Time(times, format=fmt, scale=scale)
    return pandas.DataFrame({base_field: output, "times": times}, index=timestamps.utc.datetime64)


def resample(df1, df2, interp_type='time'):
    """Resample one DataFrame onto another.

    Parameters
    ----------
    df1 : `pandas.DataFrame`
        First `pandas.DataFrame`.
    df2 : `pandas.DataFrame`
        Second `pandas.DataFrame`.
    interp_type : `str`, optional
        Type of interpolation to perform (default is 'time').

    Returns
    -------
    result : `pandas.DataFrame`
        The resulting resampling is bi-directional.
        That is the length of the resulting `pandas.DataFrame` is the
        sum of the lengths of the inputs.
    """
    df = pandas.concat([df1, df2], axis=1)  # Sort in this context does not sort the data
    df = df.sort_index()
    return df.interpolate(type=interp_type)


def rendezvous_dataframes(left, right, direction='backward', tolerance=pandas.Timedelta(days=20), **kwargs):
    """Each record in ``left`` will be extended with a corresponding record in ``right`` if one exists.
       By default, the record in ``right`` will be the most recent record in the past.  The other options
       are the closest record in the future and the nearest overall.

    Parameters
    ----------
    left: `pandas.DataFrame`
        The `pandas.DataFrame` to extend
    right: `pandas.DataFrame`
        The `pandas.DataFrame` to rendezvous with ``left``
    direction: `str`
        The direction to search for the nearest record.  Default is ``backward``.
        The other options are ``forward`` and ``nearest``.
    tolerance: `pandas.Timedelta`
        The to,e window to search for the matching record
    kwargs: `dict`
        Additional keyword arguments will be forwarded to the `pandas.merge_asof` function
    """
    return pandas.merge_asof(left, right, left_index=True, right_index=True, tolerance=tolerance,
                             direction=direction, **kwargs)
