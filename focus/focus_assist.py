import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits
import io
import sep
from .settings import SEP_MIN_AREA
import logging

def extract_source(data, max_sources=50):
    # Calculate background statistics
    data = data.astype(np.float32)

    bkg = sep.Background(data)
    signal = data - bkg
    sources = sep.extract(signal, 1.5, err=bkg.globalrms, minarea=SEP_MIN_AREA)

    # Keep at most max_sources sources distributed evenly
    if len(sources) > max_sources:
        indices = np.linspace(0, len(sources)-1, max_sources, dtype=int)
        sources = sources[indices]

    return sources, signal


def plot_aperature(data, aperture):
    mask = aperture.to_mask(method='center')
    roi_data = mask.cutout(data)
    plt.imshow(roi_data, cmap='Greys', origin='lower')
    plt.colorbar(label='Intensity')
    plt.show()


from photutils.aperture import aperture_photometry, CircularAperture, CircularAnnulus
from photutils.centroids import centroid_quadratic
from photutils.profiles import RadialProfile

APERTURE_R = 10

# my_hfd is implemented according to https://www.lost-infinity.com/night-sky-image-processing-part-6-measuring-the-half-flux-diameter-hfd-of-a-star-a-simple-c-implementation/
# phd_hfd is implemented according to OpenPHD2 https://github.com/OpenPHDGuiding/phd2/blob/5576bc0832c78b009e30687ac6b30404cb9e8fcd/star.cpp#L113
def calc_hfd(signal, aperture):
    try:
        x = aperture.positions[0]
        y = aperture.positions[1]
        
        mask = aperture.to_mask(method='subpixel')
        roi_data = mask.cutout(signal)
        dist_weighted_flux = 0
        dist_pix_pairs = []
        for (y, x), pix in np.ndenumerate(roi_data):
            dx = x - aperture.r
            dy = y - aperture.r
            dist = np.sqrt(dy*dy+dx*dx)
            if dist < APERTURE_R:
                dist_weighted_flux += pix * dist
                dist_pix_pairs.append((dist, pix))  

        # total_flux = aperture_photometry(signal, aperture)['aperture_sum'][0]
        total_flux = np.sum(roi_data)
        my_hfd = dist_weighted_flux / total_flux * 2
    except Exception as e:
        logging.error(e)
        my_hfd = -10

    try:
        half_flux = total_flux / 2
        dist_pix_pairs.sort(key=lambda x: x[0])
        prev_dist, prev_pix = 0, 0
        dist, pix  = 0, 0 
        flux_acc = 0
        for dist, pix in dist_pix_pairs:
            flux_acc += pix
            if flux_acc > half_flux:
                break
            prev_dist = dist
            prev_pix = pix
        s = (dist - prev_dist) / (pix - prev_pix)

        phd_hfd = (prev_dist + (half_flux - prev_pix) * s) * 2
    except Exception as e:
        logging.error(e)
        phd_hfd = -10
    return my_hfd, phd_hfd


def calc_fwhm(signal, aperture):
    xycen = aperture.positions
    edge_radii = np.arange(25)
    rp = RadialProfile(signal, xycen, edge_radii, mask=None)
    fwhm_value = rp.gaussian_fwhm
    return fwhm_value


def stat_for_image(fits_file_url):
    hdul = fits.open(fits_file_url, cache=False)
    data = hdul[0].data
    sources, signal = extract_source(data)

    x_coords = sources['x']
    y_coords = sources['y']
    x,y = list(zip(x_coords, y_coords))[0]

    # SEP HFD
    hfrs, flag = sep.flux_radius(signal, sources['x'], sources['y'], 
                            6.*sources['a'],
                            frac=0.5, 
                            subpix=5)
    median_sep_hfd = np.median(hfrs[flag==0]) * 2

    # FWHM and other HFD
    fwhm_values = []
    my_hfd_values = []
    phd_hfd_values = []
    for x, y in zip(x_coords, y_coords):
        aperture = CircularAperture((x, y), r=APERTURE_R)
        fwhm_value = calc_fwhm(signal, aperture)
        fwhm_values.append(fwhm_value)

        # HFD
        my_hfd, phd_hfd = calc_hfd(signal, aperture)
        my_hfd_values.append(my_hfd)
        phd_hfd_values.append(phd_hfd)
    
    median_fwhm = np.median(fwhm_values)
    median_my_hfd = np.median(my_hfd_values)
    median_phd_hfd = np.median(phd_hfd_values)

    return median_fwhm, median_sep_hfd, median_my_hfd, median_phd_hfd


def find_focus_position(focuser_positions, fwhm_curve_dp, hfd_curve_dps):
    """
    Find the focus position that minimizes the FWHM and HFD curves.
    hfd_curve_dps is a dict of HFD curves for different methods.
    """
    fwhm_fit = np.polyfit(focuser_positions, fwhm_curve_dp, 2)
    fwhm_min_value = -fwhm_fit[1] / (2 * fwhm_fit[0])

    logging.info(f"FWHM predicted focuser position is {fwhm_min_value:.2f}")

    hfd_fits = {}
    hfd_min_values = {}
    for method, hfd_curve_dp in hfd_curve_dps.items():    
        hfd_fit = np.polyfit(focuser_positions, hfd_curve_dp, 2)
        hfd_min_value = -hfd_fit[1] / (2 * hfd_fit[0])
        logging.info(f"{method} HFD predicted focuser position is {hfd_min_value:.2f}")
        hfd_fits[method] = hfd_fit
        hfd_min_values[method] = hfd_min_value

    return fwhm_min_value, hfd_min_values, fwhm_fit, hfd_fits


def plot_fit(focuser_positions, fwhm_curve_dp, hfd_curve_dps, fwhm_fit, hfd_fits):
    should_plot_fit = fwhm_fit is not None and len(fwhm_fit) > 0
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    ax1.set_ylabel('FWHM (pixels)')
    ax1.set_title('Focus vs FWHM')
    ax2.set_xlabel('Focus position')
    ax2.set_ylabel('HFD (pixels)')
    ax2.set_title('Focus vs HFD')

    x_fit = np.linspace(min(focuser_positions), max(focuser_positions), 100)

    # plot FWHM curve and fit
    ax1.plot(focuser_positions, fwhm_curve_dp, 'o')
    if should_plot_fit:
        y_fit = np.polyval(fwhm_fit, x_fit)
        ax1.plot(x_fit, y_fit, label='Fit')
        # mark the minimum value of the fits
        fwhm_min_value = -fwhm_fit[1] / (2 * fwhm_fit[0])
        ax1.axvline(fwhm_min_value, color='r', linestyle='--', label=f'Minimum FWHM: {fwhm_min_value:.2f}')

    for method, hfd_curve_dp in hfd_curve_dps.items():    
        if method == 'sep':
            c = 'r'
        elif method == 'PHD':
            c = 'g'
        else:
            c = 'b'
        # plot HFD curves and fits
        ax2.plot(focuser_positions, hfd_curve_dp, 'o', color=c, label=f'{method} HFD')
        if should_plot_fit:
            fit = hfd_fits[method]
            y_fit = np.polyval(fit, x_fit)
            ax2.plot(x_fit, y_fit, color=c, label=f'{method} HFD Fit')
            hfd_min_value = -fit[1] / (2 * fit[0])
            ax2.axvline(hfd_min_value, color=c, linestyle='--', label=f'Minimum {method} HFD: {hfd_min_value:.2f}')

    ax1.legend()
    ax2.legend()
    plt.tight_layout()
    
    image_data = io.BytesIO()
    plt.savefig(image_data, format='png')
    image_data_value = image_data.getvalue()
    image_data.close()
    return image_data_value
