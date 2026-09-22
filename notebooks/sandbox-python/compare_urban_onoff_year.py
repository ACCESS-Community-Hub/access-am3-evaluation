"""Compare urban-on vs urban-off runs for a single variable, averaged over a whole period (e.g. YYYY or YYYYMM).

Plot 1: three-panel global map (urban-on, urban-off, difference) of the annual mean.
Plot 2: time series at the grid cell with the highest urban-on value.
"""

import glob
import os
from pathlib import Path

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from cartopy.util import add_cyclic_point
from matplotlib.colors import ListedColormap

urban_on_dir = '/scratch/gb02/jl8556/cylc-run/n96e-urban-ESA/share/data/History_Data/netCDF/urbana.'
urban_off_dir = '/scratch/ce10/mjl561/cylc-run/n96-CCIland-ESAsst-urban_off/share/data/History_Data/netCDF/CCIlaa.'

DATE = 199
file_glob = f'pc{DATE}*.nc'

ncvar, ncmid = 'fld_s03i328', 283 # 1.5m air temperature on tiles
ncvar, ncmid = 'fld_s03i290', 0 # sensible heat flux on tiles

PSEUDO_LEVEL = 15  # tile index (fld_s03i290 has a pseudo_level/tile dimension); 15 = urban tile

OUTPUT_DIR = '/home/561/mjl561/git/access-am3-evaluation/notebooks/sandbox-python/plots'

def var_label(da: xr.DataArray) -> str:
    long_name = da.attrs.get("long_name", da.name)
    units = da.attrs.get("units", "")
    return f"{long_name} ({units})" if units else str(long_name)


def plot_maps(da_on: xr.DataArray, da_off: xr.DataArray, label: str) -> None:
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

    fig.suptitle(f"{label} ({DATE} mean)")

    out_path = f'{OUTPUT_DIR}/compare_urban_onoff_{ncvar}_map_{DATE}.jpg'
    fig.savefig(out_path, dpi=300, bbox_inches="tight")

    print("saved figure:", out_path)


def plot_timeseries(
    ts_on: xr.DataArray, ts_off: xr.DataArray, label: str, lat: float, lon: float
) -> None:

    plt.close('all')
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    ts_on.plot(ax=ax, label="urban on")
    ts_off.plot(ax=ax, label="urban off")
    ax.set_ylabel(label)
    ax.set_title(f"time series at lat={lat:.2f}, lon={lon:.2f} (urban-on max)")
    ax.legend()

    out_path = f'{OUTPUT_DIR}/compare_urban_onoff_{ncvar}_timeseries_{DATE}.jpg'
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    print("saved figure:", out_path)


def load_var_concat(dir_prefix: str, glob_pattern: str) -> xr.DataArray:
    paths = sorted(glob.glob(f'{dir_prefix}{glob_pattern}'))
    if not paths:
        raise FileNotFoundError(f'No files match {dir_prefix}{glob_pattern}')

    das = []
    for path in paths:
        with xr.open_dataset(path) as ds:
            da = ds[ncvar]
            if "pseudo_level" in da.dims:
                da = da.sel(pseudo_level=PSEUDO_LEVEL)
            if "time_0" in da.dims:
                da = da.rename({"time_0": "time"})
            das.append(da.load())

    return xr.concat(das, dim="time")



def main(da_on: xr.DataArray, da_off: xr.DataArray) -> None:

    label = var_label(da_on)

    # collapse every non-spatial dim (time, and any leftover concat dims from
    # combining multiple monthly/daily files) so the map is strictly 2D
    reduce_dims_on = [d for d in da_on.dims if d not in ("lat", "lon")]
    reduce_dims_off = [d for d in da_off.dims if d not in ("lat", "lon")]
    map_on = da_on.mean(dim=reduce_dims_on)
    map_off = da_off.mean(dim=reduce_dims_off)
    plot_maps(map_on, map_off, label)


    # define Sydney
    lat_val,lon_val = -33.8, 151
    # # locate the grid cell with the highest urban-on value (period-mean field)
    # max_idx = map_on.argmax(dim=["lat", "lon"])
    # lat_val = float(map_on["lat"].isel(lat=max_idx["lat"]))
    # lon_val = float(map_on["lon"].isel(lon=max_idx["lon"]))

    ts_on = da_on.sel(lat=lat_val, lon=lon_val, method='nearest')
    ts_off = da_off.sel(lat=lat_val, lon=lon_val, method='nearest')

    # calculate hourly mean
    ts_on = ts_on.groupby('time.hour').mean(dim='time')
    ts_off = ts_off.groupby('time.hour').mean(dim='time')

    # plot timeseries
    plot_timeseries(ts_on, ts_off, label, lat_val, lon_val)


if __name__ == "__main__":

    da_on = load_var_concat(urban_on_dir, file_glob)
    da_off = load_var_concat(urban_off_dir, file_glob)

    # set zero values to NaN
    da_on = da_on.where(da_on != 0)
    da_off = da_off.where(da_off != 0)

    main(da_on, da_off)
