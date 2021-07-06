from typing import Union

import numpy
import pytest
import xarray
import xarray.testing

from openeo.udf import XarrayDataCube
from .. import as_path


def test_xarraydatacube_to_dict_minimal():
    array = xarray.DataArray(numpy.zeros(shape=(2, 3)))
    xdc = XarrayDataCube(array=array)
    assert xdc.to_dict() == {
        "data": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
        "dimensions": [{"name": "dim_0"}, {"name": "dim_1"}],
    }


def test_xarraydatacube_from_dict_minimal():
    d = {"data": [[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]}
    xdc = XarrayDataCube.from_dict(d)
    assert isinstance(xdc, XarrayDataCube)
    assert xdc.id is None
    xarray.testing.assert_equal(xdc.get_array(), xarray.DataArray([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]))
    assert xdc.to_dict() == {
        "data": [[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]],
        "dimensions": [{"name": "dim_0"}, {"name": "dim_1"}],
    }


def test_xarraydatacube_to_dict():
    array = xarray.DataArray(
        numpy.zeros(shape=(2, 3)), coords={'x': [1, 2], 'y': [1, 2, 3]}, dims=('x', 'y'),
        name="testdata",
        attrs={"description": "This is an xarray with two dimensions"},
    )
    xdc = XarrayDataCube(array=array)
    assert xdc.to_dict() == {
        "id": "testdata",
        "description": 'This is an xarray with two dimensions',
        "data": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
        "dimensions": [
            {'name': 'x', 'coordinates': [1, 2]},
            {'name': 'y', 'coordinates': [1, 2, 3]},
        ],
    }


def test_xarray_datacube_from_dict():
    d = {
        "id": "testdata",
        "description": 'This is an xarray with two dimensions',
        "data": [[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]],
        "dimensions": [
            {'name': 'x', 'coordinates': [1, 2]},
            {'name': 'y', 'coordinates': [1, 2, 3]},
        ],
    }
    xdc = XarrayDataCube.from_dict(d)
    assert isinstance(xdc, XarrayDataCube)
    assert xdc.to_dict() == d


def _build_xdc(
        ts: Union[list, int] = None,
        bands: Union[list, int] = None,
        xs: Union[list, int] = None,
        ys: Union[list, int] = None,
        dtype=numpy.int32,
):
    """
    Build multi-dimensional XarrayDataCube containing given dimensions/coordinates
    """
    dims = []
    coords = {}
    value = numpy.zeros(shape=())
    for dim, cs in [("t", ts), ("bands", bands), ("x", xs), ("y", ys)]:
        if cs:
            dims.append(dim)
            if isinstance(cs, list):
                coords[dim] = cs
                cs = len(cs)
            value = 10 * value[..., None] + numpy.arange(cs)
    return XarrayDataCube(xarray.DataArray(value.astype(dtype), dims=dims, coords=coords))


def test_build_xdc():
    xarray.testing.assert_equal(
        _build_xdc(ts=2).array,
        xarray.DataArray(data=numpy.array([0, 1]), dims=["t"], coords={})
    )
    xarray.testing.assert_equal(
        _build_xdc(ts=[2019, 2020]).array,
        xarray.DataArray(data=numpy.array([0, 1]), dims=["t"], coords={"t": [2019, 2020]})
    )
    xarray.testing.assert_equal(
        _build_xdc(xs=[1, 2, 3]).array,
        xarray.DataArray(data=numpy.array([0, 1, 2]), dims=["x"], coords={"x": [1, 2, 3]})
    )
    xarray.testing.assert_equal(
        _build_xdc(ts=2, xs=3).array,
        xarray.DataArray(
            data=numpy.array([[0, 1, 2], [10, 11, 12]]),
            dims=["t", "x"], coords={}
        )
    )
    xarray.testing.assert_equal(
        _build_xdc(ts=[2019, 2020], xs=5).array,
        xarray.DataArray(
            data=numpy.array([[0, 1, 2, 3, 4], [10, 11, 12, 13, 14]]),
            dims=["t", "x"], coords={"t": [2019, 2020]}
        )
    )
    xarray.testing.assert_equal(
        _build_xdc(ts=[2019, 2020], xs=[1, 2, 3]).array,
        xarray.DataArray(
            data=numpy.array([[0, 1, 2], [10, 11, 12]]),
            dims=["t", "x"], coords={"t": [2019, 2020], "x": [1, 2, 3]}
        )
    )
    xarray.testing.assert_equal(
        _build_xdc(ts=[2019, 2020], bands=["a", "b"], xs=[1, 2, 3], ys=[20, 30]).array,
        xarray.DataArray(
            data=numpy.array([
                [
                    [[0, 1], [10, 11], [20, 21]],
                    [[100, 101], [110, 111], [120, 121]]
                ],
                [
                    [[1000, 1001], [1010, 1011], [1020, 1021]],
                    [[1100, 1101], [1110, 1111], [1120, 1121]]
                ],
            ]),
            dims=["t", "bands", "x", "y"],
            coords={"t": [2019, 2020], "bands": ["a", "b"], "x": [1, 2, 3], "y": [20, 30]}
        )
    )


def _assert_equal_after_save_and_load(xdc, tmp_path, format) -> XarrayDataCube:
    path = as_path(tmp_path / ("cube." + format))
    xdc.save_to_file(path=path, fmt=format)
    result = XarrayDataCube.from_file(path=path, fmt=format)
    xarray.testing.assert_equal(xdc.array, result.array)
    return result


@pytest.mark.parametrize("format", ["json", "netcdf"])
def test_save_load_full(format, tmp_path):
    xdc = _build_xdc(ts=[2019, 2020, 2021], bands=["a", "b"], xs=[2, 3, 4, 5], ys=[5, 6, 7, 8, 9])
    assert xdc.array.shape == (3, 2, 4, 5)
    _assert_equal_after_save_and_load(xdc, tmp_path, format)


@pytest.mark.parametrize(["filename", "save_format", "load_format"], [
    ("cube.nc", None, None),
    ("cube.NC", None, None),
    ("cube.NetCDF", None, None),
    ("cube.nc", None, "netcdf"),
    ("cube.nc", "netcdf", None),
    ("cube.json", None, None),
    ("cube.JSON", None, None),
    ("cube.json", "json", None),
    ("cube.json", None, "json"),
])
def test_save_load_guess_format(filename, save_format, load_format, tmp_path):
    xdc = _build_xdc(ts=[2019, 2020, 2021], bands=["a", "b"], xs=[2, 3, 4, 5], ys=[5, 6, 7, 8, 9])
    assert xdc.array.shape == (3, 2, 4, 5)
    path = as_path(tmp_path / filename)
    xdc.save_to_file(path, fmt=save_format)
    result = XarrayDataCube.from_file(path, fmt=load_format)
    xarray.testing.assert_equal(xdc.array, result.array)


def test_save_load_guess_format_invalid(tmp_path):
    xdc = _build_xdc(ts=[2019, 2020, 2021], bands=["a", "b"], xs=[2, 3, 4, 5], ys=[5, 6, 7, 8, 9])
    assert xdc.array.shape == (3, 2, 4, 5)
    path = as_path(tmp_path / "cube.foobar")
    with pytest.raises(ValueError, match="Can not guess format"):
        xdc.save_to_file(path)
    xdc.save_to_file(path, fmt="netcdf")
    with pytest.raises(ValueError, match="Can not guess format"):
        result = XarrayDataCube.from_file(path)
    result = XarrayDataCube.from_file(path, fmt="netcdf")
    xarray.testing.assert_equal(xdc.array, result.array)


@pytest.mark.parametrize("format", ["json", "netcdf"])
def test_save_load_no_time_labels(format, tmp_path):
    xdc = _build_xdc(ts=3, bands=["a", "b"], xs=[2, 3, 4, 5], ys=[5, 6, 7, 8, 9])
    assert xdc.array.shape == (3, 2, 4, 5)
    _assert_equal_after_save_and_load(xdc, tmp_path, format)


@pytest.mark.parametrize("format", ["json", "netcdf"])
def test_save_load_no_time_dim(format, tmp_path):
    xdc = _build_xdc(bands=["a", "b"], xs=[2, 3, 4, 5], ys=[5, 6, 7, 8, 9])
    assert xdc.array.shape == (2, 4, 5)
    _assert_equal_after_save_and_load(xdc, tmp_path, format)


@pytest.mark.parametrize("format", ["json", "netcdf"])
def test_save_load_one_band_no_labels(format, tmp_path):
    if format == "netcdf":
        # TODO fix saving procedure or test?
        pytest.skip("_save_DataArray_to_NetCDF introduces band names if they don't exist, which fails equality test")
    xdc = _build_xdc(ts=[2019, 2020, 2021], bands=1, xs=[2, 3, 4, 5], ys=[5, 6, 7, 8, 9])
    assert xdc.array.shape == (3, 1, 4, 5)
    _assert_equal_after_save_and_load(xdc, tmp_path, format)


@pytest.mark.parametrize("format", ["json", "netcdf"])
def test_save_load_two_band_no_labels(format, tmp_path):
    if format == "netcdf":
        # TODO fix saving procedure or test?
        pytest.skip("_save_DataArray_to_NetCDF introduces band names if they don't exist, which fails equality test")
    xdc = _build_xdc(ts=[2019, 2020, 2021], bands=2, xs=[2, 3, 4, 5], ys=[5, 6, 7, 8, 9])
    assert xdc.array.shape == (3, 2, 4, 5)
    _assert_equal_after_save_and_load(xdc, tmp_path, format)


@pytest.mark.parametrize("format", ["json", "netcdf"])
def test_save_load_no_band_dim(format, tmp_path):
    if format == "netcdf":
        # TODO fix saving procedure or test?
        pytest.skip("_save_DataArray_to_NetCDF introduces band dim if it doesn't exist, which fails equality test")
    xdc = _build_xdc(ts=[2019, 2020, 2021], xs=[2, 3, 4, 5], ys=[5, 6, 7, 8, 9])
    assert xdc.array.shape == (3, 4, 5)
    _assert_equal_after_save_and_load(xdc, tmp_path, format)


@pytest.mark.parametrize("format", ["json", "netcdf"])
def test_save_load_no_xy_labels(format, tmp_path):
    xdc = _build_xdc(ts=[2019, 2020, 2021], bands=["a", "b"], xs=4, ys=5)
    assert xdc.array.shape == (3, 2, 4, 5)
    _assert_equal_after_save_and_load(xdc, tmp_path, format)


@pytest.mark.parametrize("format", ["json", "netcdf"])
def test_save_load_no_xy_dim(format, tmp_path):
    xdc = _build_xdc(ts=[2019, 2020, 2021], bands=["a", "b"], )
    assert xdc.array.shape == (3, 2)
    _assert_equal_after_save_and_load(xdc, tmp_path, format)


@pytest.mark.parametrize("format", ["json", "netcdf"])
def test_save_load_dtype_int64(format, tmp_path):
    xdc = _build_xdc(ts=[2019, 2020, 2021], bands=["a", "b"], xs=[2, 3, 4, 5], ys=[5, 6, 7, 8, 9], dtype=numpy.int64)
    assert xdc.array.shape == (3, 2, 4, 5)
    result = _assert_equal_after_save_and_load(xdc, tmp_path, format)
    assert result.array.dtype == numpy.int64


@pytest.mark.parametrize("format", ["json", "netcdf"])
def test_save_load_dtype_float64(format, tmp_path):
    xdc = _build_xdc(ts=[2019, 2020, 2021], bands=["a", "b"], xs=[2, 3, 4, 5], ys=[5, 6, 7, 8, 9], dtype=numpy.float64)
    assert xdc.array.shape == (3, 2, 4, 5)
    result = _assert_equal_after_save_and_load(xdc, tmp_path, format)
    assert result.array.dtype == numpy.float64


@pytest.mark.slow
def test_datacube_plot(tmp_path):
    import matplotlib.pyplot as plt  # TODO: mandatory dev dependency or optional?

    ts = [numpy.datetime64('2020-08-01'), numpy.datetime64('2020-08-11'), numpy.datetime64('2020-08-21')]
    xdc = _build_xdc(ts=ts, bands=["a", "b"], xs=100, ys=100)
    path = as_path(tmp_path / "test.png")
    xdc.plot("title", oversample=1.2, cbartext="some\nvalue", to_file=path, to_show=False)

    png_data = plt.imread(str(path))
    # Just check basic file properties to make sure the file isn't empty.
    assert len(png_data.shape) == 3
    assert png_data.shape[0] > 100
    assert png_data.shape[1] > 100
    assert png_data.shape[2] == 4
