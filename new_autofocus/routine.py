import asyncio
import aiohttp
import numpy as np
import sep_pjw as sep
import logging
from astropy.io import fits
import os
import random
from evora.debug import DEBUGGING

TINYFOCUS_URL = "http://127.0.0.1:5000"

# Mirror the app.py pathing logic
if DEBUGGING:
    DEFAULT_PATH = './data/ecam'
else:
    DEFAULT_PATH = '/data/ecam'

async def move_focuser(steps: int):
    """Sends HTTP command to tinyfocus-server."""
    if DEBUGGING:
        logging.info(f"[DEBUG] Mock moving focuser by {steps} steps")
        return {"code": 200}

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{TINYFOCUS_URL}/api/move?steps={steps}") as resp:
            return await resp.json()

def generate_mock_debug_image():
    """Generates a 2D numpy array with noise and a random circle for debug mode."""
    img_data = np.random.randint(100, 200, (1024, 1024), dtype=np.uint16)
    radius = random.randint(5, 40)
    cy, cx = 512, 512
    y, x = np.ogrid[:1024, :1024]
    mask = (x - cx)**2 + (y - cy)**2 <= radius**2
    img_data[mask] = 50000  # bright star
    return img_data

def measure_hfd(image_data):
    try:
        data = image_data.astype(np.float64)
        bkg = sep.Background(data)
        data_sub = data - bkg
        objects = sep.extract(data_sub, 3.0, err=bkg.globalrms)
        
        if len(objects) == 0: return 99.0 
            
        flux, fluxerr, flag = sep.sum_circle(data_sub, objects['x'], objects['y'], 5.0, subpix=1, bkgann=(10.0, 15.0))
        top_indices = np.argsort(flux)[-15:] 
        
        hfr_array, _ = sep.flux_radius(data_sub, objects['x'][top_indices], objects['y'][top_indices], 6.0 * objects['a'][top_indices], 0.5, normflux=flux[top_indices], subpix=5)
        
        valid_hfr = [r for r in hfr_array if r > 0 and not np.isnan(r)]
        return np.mean(valid_hfr) * 2.0 if valid_hfr else 99.0
    except Exception as e:
        logging.error(f"HFD error: {e}")
        return 99.0

def save_temp_fits(img_data):
    """Saves the image to the disk so JS9 can load it via the file server."""
    os.makedirs(DEFAULT_PATH, exist_ok=True)
    
    file_path = f"{DEFAULT_PATH}/temp_focus.fits"
    url_path = "/data/ecam/temp_focus.fits" # Always the absolute proxy path for the frontend
    
    hdu = fits.PrimaryHDU(img_data.astype(np.uint16))
    hdu.writeto(file_path, overwrite=True)
    return url_path

async def calculate_best_focus(positions, hfds, step_size, total_steps):
    """Analyzes the array of data collected by the frontend and moves to the vertex."""
    valid_data = [(p, h) for p, h in zip(positions, hfds) if h < 90.0]
    
    if len(valid_data) < 3:
        return {"status": "error", "message": "Not enough valid stars detected."}
        
    x = np.array([d[0] for d in valid_data])
    y = np.array([d[1] for d in valid_data])
    
    a, b, c = np.polyfit(x, y, 2)
    
    if a > 0:
        vertex_x = -b / (2 * a)
        best_position = max(0, min(int(round(vertex_x)), (total_steps - 1) * step_size))
        
        current_position = max(positions)
        steps_back = current_position - best_position
            
        await move_focuser(steps_back)
        
        return {"status": "success", "best_position": best_position}
    else:
        return {"status": "error", "message": "Curve fit failed."}