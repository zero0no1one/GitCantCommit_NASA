"""Cut a 2° x 2° patch around Tranquility Base out of the LOLA 118 m (256 pixels per degree) global elevation map.

Source: USGS Astrogeology mosaic of the LRO LOLA gridded data record LDEM_256 (Mar 2014),
https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif
Simple cylindrical on a 1,737,400 m sphere, int16 with scale 0.5 m, heights above that sphere.
Smith, D. E. et al. (2010), Geophys. Res. Lett. 37, L18204, doi:10.1029/2010GL043751.

The file is stored as whole-row strips, so reading the window pulls every full row it touches (about 94 MB);
only the 2° x 2° cut is kept (source/tranquility_ldem256.npz, about 0.5 MB).
Run: python fetch_tranquility_dem.py
"""
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import Window

URL = 'https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif'
OUT = Path(__file__).resolve().parent/'source'/'tranquility_ldem256.npz'
CENTRE_LAT, CENTRE_LON = 0.674, 23.473     # Apollo 11, NSSDC, mean-Earth/polar-axis frame
HALF_DEG = 1.0
PPD = 256


def main():
    with rasterio.Env(CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif', GDAL_HTTP_MAX_RETRY=4, GDAL_HTTP_RETRY_DELAY=2):
        with rasterio.open('/vsicurl/'+URL) as ds:
            assert ds.width == 360*PPD and ds.height == 180*PPD, (ds.width, ds.height)
            row0 = int(np.floor((90-(CENTRE_LAT+HALF_DEG))*PPD))
            col0 = int(np.floor((CENTRE_LON+180-HALF_DEG)*PPD))
            size = int(2*HALF_DEG*PPD)
            raw = ds.read(1, window=Window(col0, row0, size, size))
            scale, nodata = ds.scales[0], ds.nodata
    z = np.where(raw == nodata, np.nan, raw*scale).astype(np.float32)
    # Pixel centres: row r is at latitude 90 - (row0 + r + 0.5)/PPD, column c at longitude (col0 + c + 0.5)/PPD - 180.
    north_lat = 90-(row0+.5)/PPD
    west_lon = (col0+.5)/PPD-180
    OUT.parent.mkdir(exist_ok=True)
    np.savez_compressed(OUT, z=z, north_lat=north_lat, west_lon=west_lon, ppd=PPD, source=URL)
    print(f'{OUT.name}: {z.shape}, {np.nanmin(z):.0f}..{np.nanmax(z):.0f} m, NaN {np.isnan(z).sum()}, '
          f'{OUT.stat().st_size/1e6:.2f} MB')


if __name__ == '__main__':
    main()
