import astrometry
import itertools    
from astropy.io import fits
import sep_pjw as sep
import numpy as np
import time
from .models import PlateSolvingResult, PlateSolvingResultStatus
from .settings import MAX_SOURCES, CACHE_DIR

from evora.debug import DEBUGGING

import logging
logging.basicConfig(level=logging.INFO)

def logodds_callback(logodds_list: list[float]) -> astrometry.Action:
    if len(logodds_list) < 3:
        return astrometry.Action.CONTINUE
    if logodds_list[1] > logodds_list[0] - 10 and logodds_list[2] > logodds_list[0] - 10:
        return astrometry.Action.STOP
    return astrometry.Action.CONTINUE

if not DEBUGGING:
    # Only download astrometry data if we're on production
    solver = astrometry.Solver(
        astrometry.series_5200.index_files(
            cache_directory=CACHE_DIR,
            scales={0,3},
        )
    )
else:
    solver = None


def extract_sources(data):
    start_time = time.time()

    # Estimate the background and subtract it from the image
    bkg = sep.Background(data)
    signal = data - bkg

    # Extract sources from the image
    sources = sep.extract(signal, thresh=1.5, err=bkg.globalrms, minarea=40)
    if len(sources) > MAX_SOURCES:
        indices = np.linspace(0, len(sources)-1, MAX_SOURCES, dtype=int)
        sources = sources[indices]

    logging.info(f"Number of sources found: {len(sources)}")
    x, y = sources['x'], sources['y']
    stars_xy = list(zip(x, y))

    end_time = time.time()
    logging.info(f"SE took: {end_time - start_time} seconds")

    return stars_xy

def plot_sources(data, sources):
    from matplotlib import pyplot as plt
    from astropy.visualization import AsinhStretch
    from astropy.visualization.mpl_normalize import ImageNormalize
    from photutils.aperture import CircularAperture
    positions = np.transpose((sources['x'], sources['y']))
    apertures = CircularAperture(positions, r=15.0)
    norm = ImageNormalize(stretch=AsinhStretch())
    fig = plt.figure(figsize=(10, 8))
    plt.imshow(data, cmap='Greys', origin='lower', norm=norm,
               interpolation='nearest')
    apertures.plot(color='blue', lw=1.5, alpha=0.5)
    plt.show()


def solve(solver, stars_xy, size_hint=astrometry.SizeHint(0.4, 0.5), position_hint=None):
    start_time = time.time()

    solution = solver.solve(
        stars=stars_xy,
        size_hint=size_hint,
        position_hint=position_hint,
        solution_parameters=astrometry.SolutionParameters(
            logodds_callback=logodds_callback,
        )
    )

    end_time = time.time()
    logging.info(f"Solving took: {end_time - start_time} seconds")

    return solution


def visualize_solution(solution_match, w, h) -> str:
    wcsobj = solution_match.astropy_wcs()
    r,d = solution_match.center_ra_deg, solution_match.center_dec_deg

    poly_path = [(1, 1), (w, 1), (w, h), (1, h), (1, 1)]

    # Convert pixel coordinates to world coordinates (RA, Dec)
    poly_path_sky = [wcsobj.pixel_to_world(x, y) for x, y in poly_path]
    ra_dec_chain = itertools.chain.from_iterable([(coord.ra.deg, coord.dec.deg) for coord in poly_path_sky])

    layer = 'unwise-neo6'
    rtn = ('http://legacysurvey.org/viewer/?ra=%.4f&dec=%.4f&layer=%s&poly=%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f' %
        ((r, d, layer) + tuple(ra_dec_chain)))
    return rtn


def solve_fits(file_path, position_hint=None) -> PlateSolvingResult:
    try:
        hdul = fits.open(file_path)
        data = hdul[0].data
        data = data.astype(np.float32)

        stars_xy = extract_sources(data)
        # plot_sources(data, stars_xy)
        solution = solve(solver, stars_xy, position_hint=position_hint)
        
        if not solution.has_match():
            logging.info("No match found.")
            res = PlateSolvingResult(
                status=PlateSolvingResultStatus.FAILURE,
                failure_reason="No match found."
            )
            return res
    
        best_match = solution.best_match()

        h,w = hdul[0].header['NAXIS1'], hdul[0].header['NAXIS2']
        visualization_url = visualize_solution(best_match, w, h)
        logging.info(f"{visualization_url=}")

        res = PlateSolvingResult(
            status=PlateSolvingResultStatus.SUCCESS,
            center_ra_deg=best_match.center_ra_deg,
            center_dec_deg=best_match.center_dec_deg,
            visualization_url=visualization_url,
        )
        return res

    except FileNotFoundError:
        res = PlateSolvingResult(
            status=PlateSolvingResultStatus.FAILURE,
            failure_reason="FileNotFoundError"
        )
        return res
        


if __name__ == "__main__":
    file_path = "/Users/siyu/Downloads/data/ecam/20231021/horsehead/2023-10-21T10-50-30_i_-79.25_300.0s_0093.fits"
    res = solve_fits(file_path)
    print(res.visualization_url)
