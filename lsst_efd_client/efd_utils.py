"""Free functions to help out with EFD operations.
"""

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
    df = df1.append(df2, sort=False)  # Sort in this context does not sort the data
    df = df.sort_index()
    return df.interpolate(type=interp_type)

