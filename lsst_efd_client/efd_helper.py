"""EFD client class
"""

import aioinflux
from functools import partial
import logging
import pandas as pd
from astropy.time import Time, TimeDelta

from .auth_helper import NotebookAuth


class EfdClient:
    """Class to handle connections and basic queries

    Parameters
    ----------
    efd_name : `str`
        Name of the EFD instance for which to retrieve credentials.
    db_name : `str`, optional
        Name of the database within influxDB to query ('efd' by default).
    port : `str`, optional
        Port to use when querying the database ('443' by default).
    internal_scale : `str`, optional
        Time scale to use when converting times to internal formats
        ('tai' by default).
    path_to_creds : `str`, optional
        Absolute path to use when reading credentials from disk
        ('~/.lsst/notebook_auth.yaml' by default).
    """

    influx_client = None
    """The `aioinflux.client.InfluxDBClient` used for queries.

    This should be used to execute queries not wrapped by this class.
    """

    subclasses = {}
    deployment = ''

    def __init__(self, efd_name, db_name='efd', port='443',
                 internal_scale='tai', path_to_creds='~/.lsst/notebook_auth.yaml'):
        self.db_name = db_name
        self.internal_scale = internal_scale
        self.auth = NotebookAuth(path=path_to_creds)
        host, user, password = self.auth.get_auth(efd_name)
        self.influx_client = aioinflux.InfluxDBClient(host=host,
                                                      port=port,
                                                      ssl=True,
                                                      username=user,
                                                      password=password,
                                                      db=db_name,
                                                      mode='async')  # mode='blocking')
        self.influx_client.output = 'dataframe'
        self.query_history = []

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """Register subclasses with the abstract base class.
        """
        super().__init_subclass__(**kwargs)
        if cls.mode in EfdClient.subclasses:
            raise ValueError(f'Class for mode, {cls.mode}, already defined')
        EfdClient.subclasses[cls.deployment] = cls

    def from_name(self, efd_name, *args, **kwargs):
        """Construct a client for the specific named subclass.

        Parameters
        ----------
        efd_name : `str`
            Name of the EFD instance for which to construct a client.
        *args
            Extra arguments to pass to the subclass constructor.
        **kwargs
            Extra keyword arguments to pass to the subclass constructor.

        Raises
        ------
        NotImpementedError
            Raised if there is no subclass corresponding to the name.
        """
        if efd_name not in self. subclasses:
            raise NotImplementedError(f'There is no EFD client class implemented for {efd_name}.')
        return self.subclasses[efd_name](efd_name, *args, **kwargs)

    async def _do_query(self, query):
        """Query the influxDB and return results

        Parameters
        ----------
        query : `str`
            Query string to execute.

        Returns
        -------
        results : `pandas.DataFrame`
            Results of the query in a `pandas.DataFrame`.
        """
        self.query_history.append(query)
        result = await self.influx_client.query(query)
        return result

    async def get_topics(self):
        """Query the list of possible topics.

        Returns
        -------
        results : `list`
            List of valid topics in the database.
        """
        topics = await self._do_query('SHOW MEASUREMENTS')
        return topics['name'].tolist()

    async def get_fields(self, topic_name):
        """Query the list of field names for a topic.

        Parameters
        ----------
        topic_name : `str`
            Name of topic to query for field names.

        Returns
        -------
        results : `list`
            List of field names in specified topic.
        """
        fields = await self._do_query(f'SHOW FIELD KEYS FROM "{self.db_name}"."autogen"."{topic_name}"')
        return fields['fieldKey'].tolist()

    def build_time_range_query(self, topic_name, fields, start, end, is_window=False, index=None):
        """Build a query based on a time range.

        Parameters
        ----------
        topic_name : `str`
            Name of topic for which to build a query.
        fields :  `str` or `list`
            Name of field(s) to query.
        start : `astropy.time.Time`
            Start time of the time range, if ``is_window`` is specified,
            this will be the midpoint of the range.
        end : `astropy.time.Time` or `astropy.time.TimeDelta`
            End time of the range either as an absolute time or
            a time offset from the start time.
        is_window : `bool`, optional
            If set and the end time is specified as a
            `~astropy.time.TimeDelta`, compute a range centered on the start
            time (default is `False`).
        index : `int`, optional
            For indexed topics set this to the index of the topic to query
            (default is `None`).

        Returns
        -------
        query : `str`
            A string containing the constructed query statement.
        """
        if not isinstance(start, Time):
            raise TypeError('The first time argument must be a time stamp')

        if not start.scale == self.internal_scale:
            logging.warn(f'Timestamps must be in {self.internal_scale.upper()}.  Converting...')
            start = getattr(start, self.internal_scale)

        if isinstance(end, TimeDelta):
            if is_window:
                start_str = (start - end/2).isot
                end_str = (start + end/2).isot
            else:
                start_str = start.isot
                end_str = (start + end).isot
        elif isinstance(end, Time):
            end = getattr(end, self.internal_scale)
            start_str = start.isot
            end_str = end.isot
        else:
            raise TypeError('The second time argument must be the time stamp for the end ' +
                            'or a time delta.')
        index_str = ''
        if index:
            parts = topic_name.split('.')
            index_str = f' AND {parts[-2]}ID = {index}'  # The CSC name is always the penultimate
        timespan = f"time >= '{start_str}Z' AND time <= '{end_str}Z'{index_str}"  # influxdb demands last Z

        if isinstance(fields, str):
            fields = [fields, ]
        elif isinstance(fields, bytes):
            fields = fields.decode()
            fields = [fields, ]

        # Build query here
        return f'SELECT {", ".join(fields)} FROM "{self.db_name}"."autogen"."{topic_name}" WHERE {timespan}'

    async def select_time_series(self, topic_name, fields, start, end, is_window=False, index=None):
        """Select a time series for a set of topics in a single subsystem

        Parameters
        ----------
        topic_name : `str`
            Name of topic to query.
        fields :  `str` or `list`
            Name of field(s) to query.
        start : `astropy.time.Time`
            Start time of the time range, if ``is_window`` is specified,
            this will be the midpoint of the range.
        end : `astropy.time.Time` or `astropy.time.TimeDelta`
            End time of the range either as an absolute time or
            a time offset from the start time.
        is_window : `bool`, optional
            If set and the end time is specified as a
            `~astropy.time.TimeDelta`, compute a range centered on the start
            time (default is `False`).
        index : `int`, optional
            For indexed topics set this to the index of the topic to query
            (default is `None`).

        Returns
        -------
        result : `pandas.DataFrame`
            A `pandas.DataFrame` containing the results of the query.
        """
        query = self.build_time_range_query(topic_name, fields, start, end, is_window, index)
        # Do query
        ret = await self._do_query(query)
        if not isinstance(ret, pd.DataFrame) and not ret:
            # aioinflux returns an empty dict for an empty query
            ret = pd.DataFrame()
        return ret

    async def select_top_n(self, topic_name, fields, num):
        """Select the most recent N samples from a set of topics in a single subsystem.
        This method does not guarantee sort direction of the returned rows.

        Parameters
        ----------
        topic_name : `str`
            Name of topic to query.
        fields : `str` or `list`
            Name of field(s) to query.
        num : `int`
            Number of rows to return.

        Returns
        -------
        result : `pandas.DataFrame`
            A `pandas.DataFrame` containing teh results of the query.
        """

        # The "GROUP BY" is necessary to return the tags
        limit = f"GROUP BY * ORDER BY DESC LIMIT {num}"

        if isinstance(fields, str):
            fields = [fields, ]
        elif isinstance(fields, bytes):
            fields = fields.decode()
            fields = [fields, ]

        # Build query here
        query = f'SELECT {", ".join(fields)} FROM "{self.db_name}"."autogen"."{topic_name}" {limit}'

        # Do query
        ret = await self._do_query(query)
        if not isinstance(ret, pd.DataFrame) and not ret:
            # aioinflux returns an empty dict for an empty query
            ret = pd.DataFrame()
        return ret

    def _make_fields(self, fields, base_fields):
        """Construct the list of fields for a field that
        is the result of ingesting vector data.

        Parameters
        ----------
        fields : `list`
            List of field names to search for vector field names.
        base_fields : `list`
            List of base field names to search the fields list for.

        Returns
        -------
        fields : `tuple`
            Tuple containing a dictionary keyed by the base field
            names with lists of resulting fields from the fields list
            and a single `int` representing number of entries in each
            vector (they must be the same for all base fields).
        """
        ret = {}
        n = None
        for bfield in base_fields:
            for field in fields:
                if field.startswith(bfield) and field[len(bfield):].isdigit():  # Check prefix is complete
                    ret.setdefault(bfield, []).append(field)
            if n is None:
                n = len(ret[bfield])
            if n != len(ret[bfield]):
                raise ValueError(f'Field lengths do not agree for {bfield}: {n} vs. {len(ret[bfield])}')

            def sorter(prefix, val):
                return int(val[len(prefix):])

            part = partial(sorter, bfield)
            ret[bfield].sort(key=part)
        return ret, n

    async def select_packed_time_series(self, topic_name, base_fields, start, end,
                                        is_window=False, index=None, ref_timestamp_col="cRIO_timestamp"):
        """Select fields that are time samples and unpack them into a dataframe.

        Parameters
        ----------
        topic_name : `str`
            Name of topic to query.
        base_fields :  `str` or `list`
            Base field name(s) that will be expanded to query all
            vector entries.
        start : `astropy.time.Time`
            Start time of the time range, if ``is_window`` is specified,
            this will be the midpoint of the range.
        end : `astropy.time.Time` or `astropy.time.TimeDelta`
            End time of the range either as an absolute time or
            a time offset from the start time.
        is_window : `bool`, optional
            If set and the end time is specified as a
            `~astropy.time.TimeDelta`, compute a range centered on the start
            time (default is `False`).
        index : `int`, optional
            For indexed topics set this to the index of the topic to query
            (default is `False`).
        ref_timestamp_col : `str`, optional
            Name of the field name to use to assign timestamps to unpacked
            vector fields (default is 'cRIO_timestamp').

        Returns
        -------
        result : `pandas.DataFrame`
            A `pandas.DataFrame` containing the results of the query.
        """
        fields = await self.get_fields(topic_name)
        if isinstance(base_fields, str):
            base_fields = [base_fields, ]
        elif isinstance(base_fields, bytes):
            base_fields = base_fields.decode()
            base_fields = [base_fields, ]
        qfields, els = self._make_fields(fields, base_fields)
        field_list = []
        for k in qfields:
            field_list += qfields[k]
        result = await self.select_time_series(topic_name, field_list+[ref_timestamp_col, ],
                                               start, end, is_window=is_window, index=index)
        times = []
        timestamps = []
        vals = {}
        step = 1./els
        for tstamp, row in result.iterrows():  # for large numbers of columns itertuples doesn't work
            t = getattr(row, ref_timestamp_col)
            for i in range(els):
                times.append(t + i*step)
                # We need to convert to something bokeh knows about.
                timestamps.append((Time(t, format='unix', scale=self.internal_scale) +
                                   TimeDelta(i*step, format='sec')).datetime64)
                for k in qfields:
                    fld = f'{k}{i}'
                    if fld not in qfields[k]:
                        raise ValueError(f'{fld} not in field list')
                    vals.setdefault(k, []).append(getattr(row, fld))
        vals.update({'times': times})
        return pd.DataFrame(vals, index=timestamps)
