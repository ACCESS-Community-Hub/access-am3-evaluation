#!/usr/bin/env python3
"""Plot first-timestep top-layer soil moisture for n96 vs n512."""

from __future__ import annotations

import glob
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

N96_DIR = "/g/data/gb02/public/AM3/output/control/n96"
N512_DIR = "/g/data/gb02/public/AM3/output/control/n512"
FILE_GLOB = "*pc*.nc"
STASH_ID = "m01s08i223"
LONG_NAME_MATCH = "SOIL MOISTURE"
SCRIPT_NAME = "access-am3-evaluation/notebooks/sandbox-python/plot_soil_moisture_top_n96_n512.py"
OUTPUT_FIG = "access-am3-evaluation/notebooks/sandbox-python/plots/soil_moisture_top_n96_n512.jpg"


def find_first_file(base_dir: str) -> str:
    pattern = os.path.join(base_dir, FILE_GLOB)
    matches = sorted(glob.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No files match {pattern}")
    return matches[0]


def find_soil_moisture_var(ds: xr.Dataset) -> str:
    if STASH_ID in ds.data_vars:
        return STASH_ID

    for name, var in ds.data_vars.items():
        long_name = str(var.attrs.get("long_name", "")).upper()
        if LONG_NAME_MATCH in long_name:
            return name

    raise KeyError(
        "Soil moisture variable not found. "
        "Expected m01s08i223 or a long_name containing 'SOIL MOISTURE'."
    )


def select_top_layer(da: xr.DataArray) -> xr.DataArray:
    # Select time=0 and top index for any non-horizontal dimension.
    sel: dict[str, int] = {}
    for dim in da.dims:
        dim_lower = dim.lower()
        if dim_lower in {"time", "t"}:
            sel[dim] = 0
            continue
        if dim_lower in {"lat", "latitude", "lon", "longitude", "x", "y"}:
            continue
        if da.sizes.get(dim, 1) > 1:
            sel[dim] = 0

    return da.isel(sel)


def get_xy(da: xr.DataArray):
    lon = None
    lat = None
    for name in ("lon", "longitude", "x"):
        if name in da.coords:
            lon = da.coords[name]
            break
    for name in ("lat", "latitude", "y"):
        if name in da.coords:
            lat = da.coords[name]
            break
    return lon, lat


def load_top_soil_moisture(path: str) -> tuple[xr.DataArray, str]:
    with xr.open_dataset(path) as ds:
        var_name = find_soil_moisture_var(ds)
        # Load before closing the dataset context.
        da = select_top_layer(ds[var_name]).squeeze().load()
    return da, var_name


def resolve_from_repo_root(configured_path: str) -> Path:
    # Resolve from git root and accept both "notebooks/..." and
    # "<repo-name>/notebooks/..." configured paths.
    search_starts: list[Path] = []
    if "__file__" in globals():
        search_starts.append(Path(__file__).resolve().parent)
    search_starts.append(Path.cwd().resolve())

    repo_root = None
    for start in search_starts:
        for candidate in (start, *start.parents):
            if (candidate / ".git").exists():
                repo_root = candidate
                break
        if repo_root is not None:
            break

    if repo_root is None:
        raise FileNotFoundError(
            "Could not find repository root (.git directory) from script or cwd."
        )

    rel = Path(configured_path)
    if rel.parts and rel.parts[0] == repo_root.name:
        rel = Path(*rel.parts[1:])
    return repo_root / rel


def main() -> None:
    n96_path = find_first_file(N96_DIR)
    n512_path = find_first_file(N512_DIR)

    n96_da, n96_var = load_top_soil_moisture(n96_path)
    n512_da, n512_var = load_top_soil_moisture(n512_path)

    n96_values = n96_da.load().values
    n512_values = n512_da.load().values
    vmin = np.nanmin([np.nanmin(n96_values), np.nanmin(n512_values)])
    vmax = np.nanmax([np.nanmax(n96_values), np.nanmax(n512_values)])

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)

    for ax, da, label, path, var_name in [
        (axes[0], n96_da, "n96", n96_path, n96_var),
        (axes[1], n512_da, "n512", n512_path, n512_var),
    ]:
        lon, lat = get_xy(da)
        if lon is not None and lat is not None:
            mesh = ax.pcolormesh(lon, lat, da, shading="auto", vmin=vmin, vmax=vmax)
        else:
            mesh = ax.imshow(da, origin="lower", vmin=vmin, vmax=vmax)
        ax.set_title(f"{label} top-layer soil moisture (t=0)")
        ax.set_xlabel("lon")
        ax.set_ylabel("lat")
        ax.text(
            0.01,
            -0.08,
            f"{Path(path).name} | {var_name}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8,
        )

    cbar = fig.colorbar(mesh, ax=axes.ravel().tolist(), shrink=0.9)
    cbar.set_label("soil moisture (top layer)")

    plot_user = os.environ.get("USER", "unknown")
    fig.text(
        0.5,
        -0.05,
        f"{SCRIPT_NAME} | user: {plot_user}",
        ha="center",
        va="bottom",
        fontsize=7,
        alpha=0.8,
    )

    print("n96 file:", n96_path)
    print("n512 file:", n512_path)
    print("n96 variable:", n96_var)
    print("n512 variable:", n512_var)

    output_path = resolve_from_repo_root(OUTPUT_FIG)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight", format="jpg")
    plt.close(fig)
    print("saved figure:", output_path)


if __name__ == "__main__":
    main()
