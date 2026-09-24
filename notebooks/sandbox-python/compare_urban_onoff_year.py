"""Compare urban-on vs urban-off runs for a single variable, averaged over a whole period (e.g. YYYY or YYYYMM).

Plot 1: three-panel global map (urban-on, urban-off, difference) of the annual mean.
Plot 2: time series at the grid cell with the highest urban-on value.
"""

import glob
import os
import re
from pathlib import Path

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from cartopy.util import add_cyclic_point
from matplotlib.colors import ListedColormap

urban_on_dir = '/scratch/gb02/jl8556/cylc-run/n96e-urban-ESA/share/data/History_Data/netCDF/urbana.'
urban_off_dir = '/scratch/ce10/mjl561/cylc-run/n96-CCIland-ESAsst-urban_off/share/data/History_Data/netCDF/CCIlaa.'
OUTPUT_DIR = '/home/561/mjl561/git/access-am3-evaluation/notebooks/sandbox-python/plots'
land_frac = '/g/data/gb02/public/AM3/ancils/CCI-Ancillary-Suite_OM3-025deg/n96e-urban-2026.06.19/vegetation/qrparm.veg.frac.nc'

DATE = ''  # leave blank for all, or specify part or full date string
START_DATE = '1985'  # e.g. '1985'; only the file's year is compared, month/day are ignored; leave blank for no lower bound

stream, ncvar, ncmid = 'pc', 'fld_s03i290', 0 # sensible heat flux on tiles
stream, ncvar, ncmid = 'pa', 'fld_s03i217', 0 # sensible heat flux (grid)
stream, ncvar, ncmid = 'pc', 'fld_s03i330', 0 # latent heat flux on tiles
stream, ncvar, ncmid = 'pa', 'fld_s03i234', 0 # latent heat flux (grid)

stream, ncvar, ncmid = 'pa', 'fld_s03i236', 283 # 1.5m air temperature (grid)
stream, ncvar, ncmid = 'pc', 'fld_s03i328', 283 # 1.5m air temperature on tiles

PSEUDO_LEVEL = 15  # tile index; 15 = urban tile
file_glob = f'{stream}{DATE}*.nc'

def var_label(da: xr.DataArray) -> str:
    long_name = da.attrs.get("long_name", da.name)
    units = da.attrs.get("units", "")
    return f"{long_name} ({units})" if units else str(long_name)


def plot_maps(da_on: xr.DataArray, da_off: xr.DataArray, label: str, period_str: str) -> None:
    diff = da_on - da_off
    data_min = float(min(da_on.min(), da_off.min()))
    data_max = float(max(da_on.max(), da_off.max()))
    half_range = max(abs(data_max - ncmid), abs(data_min - ncmid))
    vmin = ncmid - half_range
    vmax = ncmid + half_range
    diff_max = float(abs(diff).max())

    plt.close('all')

    nan_cmap = ListedColormap(["yellow"])

    def overlay_nans(ax, cyclic_data, cyclic_lon, lat):
        # NaN-highlight overlay: non-NaN cells stay NaN (transparent) here, so cartopy's
        # global-wrap masking (which always forces set_bad to transparent) never hides them.
        highlight = np.where(np.isnan(cyclic_data), 1.0, np.nan)
        ax.pcolormesh(
            cyclic_lon, lat, highlight,
            transform=ccrs.PlateCarree(), cmap=nan_cmap, vmin=0, vmax=1,
        )

    fig, axes = plt.subplots(
        1, 3, figsize=(18, 5), subplot_kw={"projection": ccrs.PlateCarree()},
        constrained_layout=True,
    )

    for ax, da, title in [(axes[0], da_on, "urban on"), (axes[1], da_off, "urban off")]:
        cyclic_data, cyclic_lon = add_cyclic_point(da.values, coord=da["lon"].values)
        mesh = ax.pcolormesh(
            cyclic_lon, da["lat"].values, cyclic_data,
            transform=ccrs.PlateCarree(), vmin=vmin, vmax=vmax,
            cmap="RdGy_r",
        )
        overlay_nans(ax, cyclic_data, cyclic_lon, da["lat"].values)
        ax.coastlines()
        ax.set_title(title)
    fig.colorbar(mesh, ax=axes[:2].tolist(), orientation="horizontal", shrink=0.8, label=label)

    diff_cyclic_data, diff_cyclic_lon = add_cyclic_point(diff.values, coord=diff["lon"].values)
    diff_mesh = axes[2].pcolormesh(
        diff_cyclic_lon, diff["lat"].values, diff_cyclic_data,
        transform=ccrs.PlateCarree(), vmin=-diff_max, vmax=diff_max,
        cmap="RdBu_r",
    )
    overlay_nans(axes[2], diff_cyclic_data, diff_cyclic_lon, diff["lat"].values)
    axes[2].coastlines()
    axes[2].set_title("urban on - urban off")
    fig.colorbar(diff_mesh, ax=axes[2], orientation="horizontal", shrink=0.8, label=label)

    fig.suptitle(f"{label}\nmean over {period_str}")

    out_path = f'{OUTPUT_DIR}/compare_urban_onoff_{ncvar}_map_{DATE}.jpg'
    fig.savefig(out_path, dpi=300, bbox_inches="tight")

    print("saved figure:", out_path)
    
    return


def plot_timeseries(
    ts_on: xr.DataArray, ts_off: xr.DataArray, label: str, lat: float, lon: float, period_str: str
) -> None:

    plt.close('all')
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    ts_on.plot(ax=ax, label="urban on")
    ts_off.plot(ax=ax, label="urban off")
    ax.set_ylabel(label)
    ax.set_title(f"time series at lat={lat:.2f}, lon={lon:.2f} (urban-on max)\nmean over {period_str}")
    ax.legend()

    out_path = f'{OUTPUT_DIR}/compare_urban_onoff_{ncvar}_timeseries_{DATE}.jpg'
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    print("saved figure:", out_path)

def filter_paths(dir_prefix: str, glob_pattern: str) -> list[str]:
    """Return a list of file paths matching the glob pattern, optionally filtered by START_DATE."""

    paths = sorted(glob.glob(f'{dir_prefix}{glob_pattern}'))
    if not paths:
        raise FileNotFoundError(f'No files match {dir_prefix}{glob_pattern}')
    
    if START_DATE:
        date_re = re.compile(rf'{re.escape(stream)}(.+)\.nc$')
        filtered_paths = []
        for path in paths:
            match = date_re.search(os.path.basename(path))
            token = match.group(1) if match else None
            year_match = re.match(r'(\d{4})', token) if token else None
            year = year_match.group(1) if year_match else None
            if year and year >= START_DATE:
                filtered_paths.append(path)
        paths = filtered_paths
        if not paths:
            raise FileNotFoundError(
                f'No files on/after START_DATE={START_DATE} match {dir_prefix}{glob_pattern}'
            )
    
    return paths


def load_var_concat(dir_prefix: str, glob_pattern: str) -> xr.DataArray:
    """Load and concatenate a variable from multiple netCDF files matching the glob pattern."""

    paths = filter_paths(dir_prefix, glob_pattern)
    print(f"loading {len(paths)} files from {dir_prefix} matching {glob_pattern}")

    das = []
    for path in paths:
        with xr.open_dataset(path) as ds:
            try:
                da = ds[ncvar]
            except KeyError:
                raise KeyError(f"Variable {ncvar} not found in {path}")
            if "pseudo_level" in da.dims:
                da = da.sel(pseudo_level=PSEUDO_LEVEL)
            if "time_0" in da.dims:
                da = da.rename({"time_0": "time"})
            print(f"loading {path}")
            das.append(da.load())

    return xr.concat(das, dim="time")


def main(da_on: xr.DataArray, da_off: xr.DataArray) -> None:

    label = var_label(da_on)

    time_start = str(da_on["time"].values.min())[:10]
    time_end = str(da_on["time"].values.max())[:10]
    period_str = f"{time_start} to {time_end}"

    # collapse every non-spatial dim (time, and any leftover concat dims from
    # combining multiple monthly/daily files) so the map is strictly 2D
    reduce_dims = [d for d in da_on.dims if d not in ("lat", "lon")]
    print(f"mean through {reduce_dims}")
    map_on = da_on.mean(dim=reduce_dims)
    map_off = da_off.mean(dim=reduce_dims)
    plot_maps(map_on, map_off, label, period_str)


    lat,lon = -33.8, 151 # sydney
    lat,lon = 40.62, 287.8 # new york
    # # locate the grid cell with the highest urban-on value (period-mean field)
    # max_idx = map_on.argmax(dim=["lat", "lon"])
    # lat_val = float(map_on["lat"].isel(lat=max_idx["lat"]))
    # lon_val = float(map_on["lon"].isel(lon=max_idx["lon"]))

    ts_on = da_on.sel(lat=lat, lon=lon, method='nearest')
    ts_off = da_off.sel(lat=lat, lon=lon, method='nearest')

    # calculate hourly mean
    ts_on = ts_on.groupby('time.hour').mean(dim='time')
    ts_off = ts_off.groupby('time.hour').mean(dim='time')

    # plot timeseries
    plot_timeseries(ts_on, ts_off, label, lat_val, lon_val, period_str)

    return

if __name__ == "__main__":

    from dask_setup import setup_dask_client
    client, cluster, dask_tmp = setup_dask_client(mode="interactive", workload_type="cpu")

    da_on = load_var_concat(urban_on_dir, file_glob)
    da_off = load_var_concat(urban_off_dir, file_glob)

    # ensure on and off are over same time period
    common_times = np.intersect1d(da_on["time"], da_off["time"])
    da_on = da_on.sel(time=common_times)
    da_off = da_off.sel(time=common_times)

    # set zero values to NaN
    da_on = da_on.where(da_on != 0)
    da_off = da_off.where(da_off != 0)

    main(da_on, da_off)
