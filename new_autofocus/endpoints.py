from evora.debug import DEBUGGING

if DEBUGGING:
    from evora.dummy import Dummy as andor 
else:
    from evora import andor

from flask import Blueprint, request, jsonify
import logging
from .routine import measure_hfd, move_focuser, calculate_best_focus, save_temp_fits, generate_mock_debug_image
from andor_routines import acquisition

blueprint = Blueprint('autofocus', __name__)

@blueprint.route('/autofocus/step', methods=['POST'])
async def autofocus_step():
    """Takes 1 picture, measures HFD, saves temp file, and moves motor 1 step."""
    req = request.get_json(force=True) if request.is_json else {}
    exposure = float(req.get('exposure', 1.0))
    step_size = int(req.get('step_size', 500))
    is_last_step = req.get('is_last_step', False)

    # take exposure
    if DEBUGGING:
        img_data = generate_mock_debug_image()
    else:
        dim = andor.getDetector()['dimensions']
        result = acquisition(dim, exposure_time=exposure)
        if result.get("status") != 20002:
            return jsonify({"status": "error", "message": "Camera acquisition failed."}), 500
        img_data = result["data"]
    
    # measures hfd
    hfd = measure_hfd(img_data)
    
    # save temp file
    file_url = save_temp_fits(img_data)
    
    # moves focuser
    if not is_last_step:
        await move_focuser(-step_size)

    return jsonify({
        "status": "success", 
        "hfd": hfd, 
        "image_url": file_url
    })

@blueprint.route('/autofocus/analyze', methods=['POST'])
async def autofocus_analyze():
    """Takes the array of data from the frontend and finishes the job."""
    req = request.get_json(force=True) if request.is_json else {}
    positions = req.get('positions', [])
    hfds = req.get('hfds', [])
    step_size = req.get('step_size', 10)
    total_steps = req.get('total_steps', 20)
    
    result = await calculate_best_focus(positions, hfds, step_size, total_steps)
    return jsonify(result)