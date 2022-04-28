#!/usr/bin/env python

"""Tests for `lsst_efd_client` package."""

import numpy
import pandas as pd
import json
import pytest
from kafkit.registry.sansio import MockRegistryApi
from astropy.time import Time, TimeDelta
import astropy.units as u
from aioinflux import InfluxDBClient
import pathlib

from lsst_efd_client import NotebookAuth, EfdClient, resample, rendezvous_dataframes

PATH = pathlib.Path(__file__).parent.absolute()


@pytest.fixture
def auth_creds():
    """Sample pytest fixture to construct credentials to run tests on.

    See more at: http://doc.pytest.org/en/latest/fixture.html
    """
    return NotebookAuth().get_auth('test_efd')


@pytest.fixture
def auth_client():
    """Sample pytest fixture to construct an auth helper to run tests on.
    """
    return NotebookAuth()


@pytest.fixture
@pytest.mark.vcr
async def efd_client():
    df = pd.read_hdf(PATH/'efd_test.hdf')
    async with InfluxDBClient(db='client_test', mode='async', output='dataframe') as client:
        await client.create_database()
        await client.write(df, measurement='lsst.sal.fooSubSys.test')
        efd_client = EfdClient('test_efd', db_name='client_test', client=client)
        # Monkey patch the client to point to an existing schema registry
        # Note this is only available if on the NCSA VPN
        efd_client.schema_registry = 'https://lsst-schema-registry-efd.ncsa.illinois.edu'
        yield efd_client
        await client.drop_database()


@pytest.fixture
def expected_strs():
    expected = []
    with open(PATH/'expected.txt', 'r') as fh:
        for line in fh.readlines():
            expected.append(line)
    return expected


@pytest.fixture
def test_df():
    return pd.read_hdf(PATH/'efd_test.hdf')


@pytest.fixture
def test_query_res():
    return pd.read_hdf(PATH/'packed_data.hdf', key='test_data')


@pytest.fixture
def start_stop():
    time = Time('2020-01-28T23:07:19.00', format='isot', scale='utc')
    return (time, time + TimeDelta(600, format='sec'))


def test_bad_endpoint():
    with pytest.raises(IOError):
        NotebookAuth(service_endpoint="https://no.path.here.net.gov")


@pytest.mark.vcr
def test_auth_host(auth_creds):
    assert auth_creds[0] == 'foo.bar.baz.net'


@pytest.mark.vcr
def test_auth_registry(auth_creds):
    assert auth_creds[1] == 'https://schema-registry-foo.bar.baz'


@pytest.mark.vcr
def test_auth_port(auth_creds):
    assert auth_creds[2] == '443'


@pytest.mark.vcr
def test_auth_user(auth_creds):
    assert auth_creds[3] == 'foo'


@pytest.mark.vcr
def test_auth_password(auth_creds):
    assert auth_creds[4] == 'bar'


@pytest.mark.vcr
def test_auth_list(auth_client):
    # Make sure there is at least one set of credentials
    # other than the test one used here
    assert len(auth_client.list_auth()) > 1


@pytest.mark.vcr
def test_efd_names(auth_client):
    # Don't assume same order in case we change
    # the backend to something that doesn't
    # guarantee that
    for name in EfdClient.list_efd_names():
        assert name in auth_client.list_auth()


@pytest.mark.vcr
def test_build_query(efd_client, start_stop, expected_strs):
    # Check passing a single field works
    qstr = efd_client.build_time_range_query('lsst.sal.fooSubSys.test', 'foo',
                                             start_stop[0], start_stop[1])
    assert qstr == expected_strs[0].strip()
    # Check passing a list of fields works
    qstr = efd_client.build_time_range_query('lsst.sal.fooSubSys.test', ['foo', 'bar'],
                                             start_stop[0], start_stop[1])
    assert qstr == expected_strs[1].strip()


@pytest.mark.vcr
def test_build_query_delta(efd_client, start_stop, expected_strs):
    tdelta = TimeDelta(250, format='sec')
    # Check passing a time delta works
    qstr = efd_client.build_time_range_query('lsst.sal.fooSubSys.test', ['foo', 'bar'],
                                             start_stop[0], tdelta)
    assert qstr == expected_strs[2].strip()
    # Check passing a time delta as a window works
    qstr = efd_client.build_time_range_query('lsst.sal.fooSubSys.test', ['foo', 'bar'],
                                             start_stop[0], tdelta, is_window=True)
    assert qstr == expected_strs[3].strip()


@pytest.mark.asyncio
async def test_parse_schema(efd_client):
    """Test the EfdClient._parse_schema method."""
    # Body that we expect the registry API to return given the request.
    expected_body = {
        "schema": json.dumps(
             {
                "name": "schema1",
                "type": "record",
                "fields": [{"name": "a", "type": "int", "description": "Description 1", "units": "second"},
                           {"name": "b", "type": "double", "description": "Description 2", "units": "meter"},
                           {"name": "c", "type": "float", "description": "Description 3", "units": "gram"},
                           {"name": "d", "type": "string", "description": "Description 4", "units": "torr"}
                           ],
              }
        ),
        "subject": "schema1",
        "version": 1,
        "id": 2,
    }

    body = json.dumps(expected_body).encode("utf-8")
    client = MockRegistryApi(body=body)

    schema = await client.get_schema_by_subject("schema1")
    result = efd_client._parse_schema("schema1", schema)
    assert isinstance(result, pd.DataFrame)
    for i, l in enumerate('abcd'):
        assert result['name'][i] == l
    for i in range(4):
        assert result['description'][i] == f'Description {i+1}'
    assert 'units' in result.columns
    assert 'aunits' in result.columns
    assert 'type' not in result.columns
    for unit in result['aunits']:
        assert isinstance(unit, u.UnitBase)


@pytest.mark.asyncio
async def test_bad_units(efd_client):
    """Test that the EfdClient._parse_schema method raises when a bad astropy unit definition is passed."""
    # Body that we expect the registry API to return given the request.
    expected_body = {
        "schema": json.dumps(
             {
                "name": "schema1",
                "type": "record",
                "fields": [{"name": "a", "type": "int", "description": "Description 1", "units": "not_unit"},
                           ],
              }
        ),
        "subject": "schema1",
        "version": 1,
        "id": 2,
    }

    body = json.dumps(expected_body).encode("utf-8")
    client = MockRegistryApi(body=body)

    schema = await client.get_schema_by_subject("schema1")
    with pytest.raises(ValueError):
        efd_client._parse_schema("schema1", schema)


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_topics(efd_client):
    topics = await efd_client.get_topics()
    assert len(topics) == 1
    assert topics[0] == 'lsst.sal.fooSubSys.test'


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_fields(efd_client, test_df):
    columns = await efd_client.get_fields('lsst.sal.fooSubSys.test')
    for c in test_df.columns:
        assert c in columns


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_time_series(efd_client, start_stop):
    df = await efd_client.select_time_series('lsst.sal.fooSubSys.test', ['foo', 'bar'],
                                             start_stop[0], start_stop[1])
    assert len(df) == 600
    for c in ['foo', 'bar']:
        assert c in df.columns
    df_legacy = await efd_client.select_time_series('lsst.sal.fooSubSys.test', ['foo', 'bar'],
                                                    start_stop[0], start_stop[1], convert_influx_index=True)
    # Test that df_legacy is in UTC assuming df was in TAI
    t = Time(df.index).unix - Time(df_legacy.index).unix
    # The indexes should all be the same since both the time range and index were shifted
    assert numpy.all(t == 0.)
    # But the queries should be different
    assert not efd_client.query_history[-2] == efd_client.query_history[-1]


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_top_n(efd_client, start_stop):
    df = await efd_client.select_top_n('lsst.sal.fooSubSys.test', ['foo', 'bar'], 10)
    assert len(df) == 10
    for c in ['foo', 'bar']:
        assert c in df.columns
    df_legacy = await efd_client.select_top_n('lsst.sal.fooSubSys.test', ['foo', 'bar'],
                                              10, convert_influx_index=True)
    # Test that df_legacy is in UTC assuming df was in TAI
    t = Time(df.index).unix - Time(df_legacy.index).unix
    assert numpy.all(t == 37.)
    df = await efd_client.select_top_n('lsst.sal.fooSubSys.test', ['foo', 'bar'], 10, time_cut=start_stop[0])
    assert len(df) == 10
    for c in ['foo', 'bar']:
        assert c in df.columns
    assert df['foo'].values[0] == 144.11835565266966
    assert df['bar'].values[0] == 631.1982694645203
    assert df['foo'].values[-1] == 180.95267940509046
    assert df['bar'].values[-1] == 314.7001662962593


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_packed_time_series(efd_client, start_stop, test_query_res):
    df_exp = test_query_res
    df = await efd_client.select_packed_time_series('lsst.sal.fooSubSys.test', ['ham', 'egg', 'hamegg'],
                                                    start_stop[0], start_stop[1])
    # The column 'times' holds the input to the packed time index.
    # It's typically in TAI, but the returned index should be in UTC
    assert numpy.all((numpy.array(df['times']) - Time(df.index).unix) == 37.)
    assert numpy.all((df.index[1:] - df.index[:-1]).total_seconds() > 0)
    assert numpy.all(df == df_exp)
    for c in ['ham', 'egg']:
        assert c in df.columns


def test_resample(test_query_res):
    df = test_query_res
    df_copy = df.copy()
    df_copy.set_index(df_copy.index + pd.Timedelta(0.05, unit='s'), inplace=True)
    df_out = resample(df, df_copy)
    assert len(df_out) == 2*len(df)


def test_rendezvous(test_df):
    sub = test_df.iloc[[25, 75], :]
    # this makes sure the index is not the same, which is the
    # point of this helper method
    sub.set_index(sub.index + pd.Timedelta(0.5, unit='s'), inplace=True)
    merged = rendezvous_dataframes(test_df, sub)
    for i, rec in enumerate(merged.iterrows()):
        if i < 26:
            assert numpy.isnan(rec[1]['ham0_y'])
            assert numpy.isnan(rec[1]['egg0_y'])
        elif i > 25 and i < 76:
            assert rec[1]['ham0_y'] == sub['ham0'][0]
            assert rec[1]['egg0_y'] == sub['egg0'][0]
        elif i > 75:
            assert rec[1]['ham0_y'] == sub['ham0'][1]
            assert rec[1]['egg0_y'] == sub['egg0'][1]
