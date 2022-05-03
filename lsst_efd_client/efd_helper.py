"""EFD client class
"""

import aiohttp
import aioinflux
from astropy.time import Time, TimeDelta
import astropy.units as u
from functools import partial
from kafkit.registry.aiohttp import RegistryApi
import pandas as pd
import requests

from .auth_helper import NotebookAuth
from .efd_utils import merge_packed_time_series


class EfdClient:
    """Class to handle connections and basic queries

    Parameters
    ----------
    efd_name : `str`
        Name of the EFD instance for which to retrieve credentials.
    db_name : `str`, optional
        Name of the database within influxDB to query ('efd' by default).
    creds_service : `str`, optional
        URL to the service to retrieve credentials
        (``https://roundtable.lsst.codes/segwarides/`` by default).
    client : `object`, optional
        An instance of a class that ducktypes as `aioinflux.InfluxDBClient`.
        The intent is to be able to substitute a mocked client for testing.
    """

    influx_client = None
    """The `aioinflux.client.InfluxDBClient` used for queries.

    This should be used to execute queries not wrapped by this class.
    """

    subclasses = {}
    deployment = ''

    def __init__(self, efd_name, db_name='efd',
                 creds_service='https://roundtable.lsst.codes/segwarides/',
                 client=None):
        self.db_name = db_name
        self.auth = NotebookAuth(service_endpoint=creds_service)
        host, schema_registry, port, user, password = self.auth.get_auth(efd_name)
        if schema_registry[-1] == '/':
            self.schema_registry = schema_registry[-1] + ':' + port + '/'
        else:
            self.schema_registry = schema_registry + ':' + port
        if client is None:
            health_url = f'https://{host}:{port}/health'
            response = requests.get(health_url)
            if response.status_code != 200:
                raise RuntimeError(f'InfluxDB server, {host}, does not appear ready to '
                                   f'recieve queries.  Recieved code:{response.status_code} '
                                   'when attempting the health check.')
            self.influx_client = aioinflux.InfluxDBClient(host=host,
                                                          port=port,
                                                          ssl=True,
                                                          username=user,
                                                          password=password,
                                                          db=db_name,
                                                          mode='async')  # mode='blocking')
            self.influx_client.output = 'dataframe'
        else:
            self.influx_client = client
        self.query_history = []

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """Register subclasses with the abstract base class.
        """
        super().__init_subclass__(**kwargs)
        if cls.mode in EfdClient.subclasses:
            raise ValueError(f'Class for mode, {cls.mode}, already defined')
        EfdClient.subclasses[cls.deployment] = cls

    @classmethod
    def list_efd_names(cls, creds_service='https://roundtable.lsst.codes/segwarides/'):
        """List all valid names for EFD deployments available.

        Parameters
        ----------
        creds_service : `str`, optional

        Returns
        -------
        results : `list`
            A `list` of `str` each specifying the name of a valid deployment.
        """
        return NotebookAuth(service_endpoint=creds_service).list_auth()

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

    async def _do_query(self, query, convert_influx_index=False):
        """Query the influxDB and return results

        Parameters
        ----------
        query : `str`
            Query string to execute.
        convert_influx_index : `bool`
            Legacy flag to convert time index from TAI to UTC

        Returns
        -------
        results : `pandas.DataFrame`
            Results of the query in a `pandas.DataFrame`.
        """
        self.query_history.append(query)
        result = await self.influx_client.query(query)
        if not isinstance(result, pd.DataFrame) and not result:
            # aioinflux returns an empty dict for an empty query
            result = pd.DataFrame()
        elif convert_influx_index:
            times = Time(result.index, format='datetime', scale='tai')
            result = result.set_index(times.utc.datetime)
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

    def build_time_range_query(self, topic_name, fields, start, end, is_window=False,
                               index=None, convert_influx_index=False):
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
            When index is used, add an 'AND {CSCName}ID = index' to the query.
            (default is `None`).
        convert_influx_index : `bool`, optional
            Convert influxDB time index from TAI to UTC?  This is for using legacy
            instances that may still have timestamps stored internally as TAI.
            Modern instances all store index timestamps as UTC natively.
            Default is `False`, don't translate from TAI to UTC.

        Returns
        -------
        query : `str`
            A string containing the constructed query statement.
        """
        if not isinstance(start, Time):
            raise TypeError('The first time argument must be a time stamp')

        if not start.scale == 'utc':
            raise ValueError('Timestamps must be in UTC.')

        if convert_influx_index:  # Implies index is in TAI, so query should be in TAI
            start = start.tai

        if isinstance(end, TimeDelta):
            if is_window:
                start_str = (start - end/2).isot
                end_str = (start + end/2).isot
            else:
                start_str = start.isot
                end_str = (start + end).isot
        elif isinstance(end, Time):
            if not end.scale == 'utc':
                raise ValueError('Timestamps must be in UTC.')
            if convert_influx_index:
                end = end.tai
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

    async def select_time_series(self, topic_name, fields, start, end, is_window=False,
                                 index=None, convert_influx_index=False):
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
            When index is used, add an 'AND {CSCName}ID = index' to the query.
            (default is `None`).
        convert_influx_index : `bool`, optional
            Convert influxDB time index from TAI to UTC?  This is for using legacy
            instances that may still have timestamps stored internally as TAI.
            Modern instances all store index timestamps as UTC natively.
            Default is `False`, don't translate from TAI to UTC.

        Returns
        -------
        result : `pandas.DataFrame`
            A `pandas.DataFrame` containing the results of the query.
        """
        query = self.build_time_range_query(topic_name, fields, start, end, is_window,
                                            index, convert_influx_index)
        # Do query
        ret = await self._do_query(query, convert_influx_index)
        return ret

    async def select_top_n(self, topic_name, fields, num, time_cut=None,
                           index=None, convert_influx_index=False):
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
        time_cut : `astropy.time.Time`, optional
            Use a time cut instead of the most recent entry.
            (default is `None`)
        index : `int`, optional
            When index is used, add an 'AND {CSCName}ID = index' to the query.
            (default is `None`).
        convert_influx_index : `bool`, optional
            Convert influxDB time index from TAI to UTC?  This is for using legacy
            instances that may still have timestamps stored internally as TAI.
            Modern instances all store index timestamps as UTC natively.
            Default is `False`, don't translate from TAI to UTC.

        Returns
        -------
        result : `pandas.DataFrame`
            A `pandas.DataFrame` containing teh results of the query.
        """

        # The "GROUP BY" is necessary to return the tags
        limit = f"GROUP BY * ORDER BY DESC LIMIT {num}"

        # Deal with time cut and index
        pstr = ''
        if time_cut:
            pstr = f" WHERE time < '{time_cut}Z'"
        if index:
            parts = topic_name.split('.')
            # The CSC name is always the penultimate
            istr = f'{parts[-2]}ID = {index}'
            if pstr != '':
                pstr += f' AND {istr}'
            else:
                pstr = f' WHERE {istr}'

        if isinstance(fields, str):
            fields = [fields, ]
        elif isinstance(fields, bytes):
            fields = fields.decode()
            fields = [fields, ]

        # Build query here
        query = f'SELECT {", ".join(fields)} FROM "{self.db_name}"."autogen"."{topic_name}"{pstr} {limit}'

        # Do query
        ret = await self._do_query(query, convert_influx_index)
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
            for f in fields:
                if f.startswith(bfield) and f[len(bfield):].isdigit():  # Check prefix is complete
                    ret.setdefault(bfield, []).append(f)
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
                                        is_window=False, index=None, ref_timestamp_col="cRIO_timestamp",
                                        ref_timestamp_fmt='unix_tai', ref_timestamp_scale='tai',
                                        convert_influx_index=False):
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
            When index is used, add an 'AND {CSCName}ID = index' to the query.
            (default is `None`).
        ref_timestamp_col : `str`, optional
            Name of the field name to use to assign timestamps to unpacked
            vector fields (default is 'cRIO_timestamp').
        ref_timestamp_fmt : `str`, optional
            Format to use to translating ``ref_timestamp_col`` values
            (default is 'unix_tai').
        ref_timestamp_scale : `str`, optional
            Time scale to use in translating ``ref_timestamp_col`` values
            (default is 'tai').
        convert_influx_index : `bool`, optional
            Convert influxDB time index from TAI to UTC?  This is for using legacy
            instances that may still have timestamps stored internally as TAI.
            Modern instances all store index timestamps as UTC natively.
            Default is `False`, don't translate from TAI to UTC.

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
                                               start, end, is_window=is_window, index=index,
                                               convert_influx_index=convert_influx_index)
        vals = {}
        for f in base_fields:
            df = merge_packed_time_series(result, f, ref_timestamp_col=ref_timestamp_col,
                                          fmt=ref_timestamp_fmt, scale=ref_timestamp_scale)
            vals[f] = df[f]
        vals.update({'times': df['times']})
        return pd.DataFrame(vals, index=df.index)

    async def get_schema(self, topic):
        """Givent a topic, get a list of dictionaries describing the fields

        Parameters
        ----------
        topic : `str`
            The name of the topic to query.  A full list of valid topic names
            can be obtained using ``get_schema_topics``.

        Returns
        -------
        result : `Pandas.DataFrame`
            A dataframe with the schema information for the topic.  One row per field.
        """
        async with aiohttp.ClientSession() as http_session:
            registry_api = RegistryApi(
                session=http_session, url=self.schema_registry
            )
            schema = await registry_api.get_schema_by_subject(f'{topic}-value')
            return self._parse_schema(topic, schema)

    @staticmethod
    def _parse_schema(topic, schema):
        # A helper function so we can test our parsing
        fields = schema['schema']['fields']
        vals = {'name': [], 'description': [], 'units': [], 'aunits': [], 'is_array': []}
        for f in fields:
            vals['name'].append(f['name'])
            if 'description' in f:
                vals['description'].append(f['description'])
            else:
                vals['description'].append(None)
            if 'units' in f:
                vals['units'].append(f['units'])
                # Special case not having units
                if vals['units'][-1] == 'unitless' or vals['units'][-1] == 'dimensionless':
                    vals['aunits'].append(u.dimensionless_unscaled)
                else:
                    vals['aunits'].append(u.Unit(vals['units'][-1]))
            else:
                vals['units'].append(None)
                vals['aunits'].append(None)
            if isinstance(f['type'], dict) and f['type']['type'] == 'array':
                vals['is_array'].append(True)
            else:
                vals['is_array'].append(False)
        return pd.DataFrame(vals)
