#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Date: 2026-11-19
# @Filename: measure.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from dataclasses import dataclass

from typing import Sequence

import numpy as np
import sep
from astropy.modeling import fitting, models


MAX_STAR_SHIFT_PX = 32
NO_STAR_IN_IMAGE = "No star in the image."

_SEP_THRESHOLD = 3.0
_SEP_MIN_AREA = 9

# Kron aperture: first moment of the light inside 6 detection radii,
# times 2.5, and at least 3.5 radii. For a Gaussian, r_1 = sqrt(pi/2),
# so 2.5 r_1 is about 3.1 sigma and the floor of 3.5 sigma holds >99% of the light.
_KRON_WINDOW = 6.0
_KRON_FACTOR = 2.5
_KRON_MIN_SCALE = 3.5

_BOX_PADDING_PX = 2
_MIN_DYNAMIC_BOX = 9

# One-pixel rings about the fitted center. Center brightness is the mean
# inside r < 1.5. A donut has its brightest ring at r >= 3, with the center
# fainter than 80% of that ring.
_RADIAL_CENTER_PX = 1.5
_DONUT_MIN_RING_PX = 3
_DONUT_CENTER_FRACTION = 0.8
_MIN_RING_PIXELS = 4

# A donut is often two detections, one on each bright side. A later detection
# whose center falls inside an earlier star's box is that same star.
# Unresolved spikes are not stars. The frame is a donut when the brightest
# star is, or when two of the brightest distinct stars are: one stray
# detection is not enough, and the bright star can hide a shallow hole.
_DONUT_SAMPLE = 8
_DONUT_VOTE_COUNT = 2
_MIN_STAR_SIGMA = 1.0


class MeasureError(Exception):
    pass


@dataclass(frozen=True)
class StarMeasurement:
    x: float
    y: float
    sigma: float
    sigma_x: float
    sigma_y: float
    amplitude: float
    gauss_x: float
    gauss_y: float
    box_origin_x: int
    box_origin_y: int
    box_size: int
    donut: bool
    star_donut: bool
    center_ratio: float
    ring_radius: int
    donut_votes: int
    stars_checked: int
    stars: tuple[SampledStar, ...]


@dataclass(frozen=True)
class SampledStar:
    x: float
    y: float
    flux: float
    sigma: float
    box_origin_x: int
    box_origin_y: int
    box_size: int
    gauss_x: float
    gauss_y: float
    center_ratio: float
    ring_radius: int
    donut: bool


@dataclass(frozen=True)
class RadialProfile:
    radii: np.ndarray
    means: np.ndarray
    center: float
    ring_radius: int
    ring_mean: float
    ratio: float
    donut: bool


@dataclass(frozen=True)
class FocusRecommendation:
    position: int
    sigma: float
    curve_ok: bool
    message: str
    curve: list[tuple[float, float]]


def measure_star(
    image: np.ndarray,
    previous_center: tuple[float, float] | None = None,
    box_size: int | tuple[int, int] | None = None,
) -> StarMeasurement:
    side = None if box_size is None else _square_side(box_size)
    signal, sources, segmap = _extract(image)
    if len(sources) == 0:
        raise MeasureError(NO_STAR_IN_IMAGE)

    index = int(np.argmax(sources["flux"]))
    star = sources[index]
    x = float(star["x"])
    y = float(star["y"])
    _check_shift(x, y, previous_center)
    if side is None:
        side = _dynamic_box_side(signal, star, segmap)

    origin_x, origin_y, cut = _cut_box(signal, x, y, side)
    sigma_x, sigma_y, amplitude, gauss_x, gauss_y = _fit_gaussian(cut, side)
    profile = radial_profile(cut, gauss_x, gauss_y)
    sample = sample_stars(signal, sources, segmap)
    votes = sum(star.donut for star in sample)
    return StarMeasurement(
        x=x,
        y=y,
        sigma=(sigma_x + sigma_y) / 2.0,
        sigma_x=sigma_x,
        sigma_y=sigma_y,
        amplitude=amplitude,
        gauss_x=gauss_x,
        gauss_y=gauss_y,
        box_origin_x=origin_x,
        box_origin_y=origin_y,
        box_size=side,
        donut=bool(profile.donut or votes >= _DONUT_VOTE_COUNT),
        star_donut=profile.donut,
        center_ratio=profile.ratio,
        ring_radius=profile.ring_radius,
        donut_votes=votes,
        stars_checked=len(sample),
        stars=tuple(sample),
    )


def radial_profile(cut: np.ndarray, x: float, y: float) -> RadialProfile:
    values = np.asarray(cut, dtype=float)
    height, width = values.shape
    yy, xx = np.mgrid[0:height, 0:width]
    radius = np.hypot(xx - x, yy - y)
    margin = min(float(x), float(y), width - 1.0 - float(x), height - 1.0 - float(y))
    n_rings = int(np.floor(margin))
    means = np.full(n_rings, np.nan)
    for index in range(n_rings):
        chosen = (radius >= index) & (radius < index + 1)
        if int(np.count_nonzero(chosen)) < _MIN_RING_PIXELS:
            continue
        means[index] = float(np.mean(values[chosen]))

    center_pixels = radius < _RADIAL_CENTER_PX
    center = (
        float(np.mean(values[center_pixels])) if np.any(center_pixels) else float("nan")
    )
    empty = RadialProfile(
        radii=np.arange(n_rings, dtype=float) + 0.5,
        means=means,
        center=center,
        ring_radius=-1,
        ring_mean=float("nan"),
        ratio=float("nan"),
        donut=False,
    )
    if n_rings < 2:
        return empty

    outer = np.array(means[1:], copy=True)
    finite = np.isfinite(outer)
    if not np.any(finite):
        return empty
    outer[~finite] = -np.inf
    ring_radius = int(np.argmax(outer)) + 1
    ring_mean = float(means[ring_radius])
    if not np.isfinite(ring_mean) or ring_mean <= 0 or not np.isfinite(center):
        return empty

    ratio = center / ring_mean
    donut = bool(ring_radius >= _DONUT_MIN_RING_PX and ratio < _DONUT_CENTER_FRACTION)
    return RadialProfile(
        radii=empty.radii,
        means=means,
        center=center,
        ring_radius=ring_radius,
        ring_mean=ring_mean,
        ratio=float(ratio),
        donut=donut,
    )


def sample_stars(
    signal: np.ndarray,
    sources: np.ndarray,
    segmap: np.ndarray,
) -> list[SampledStar]:
    order = np.argsort(sources["flux"])[::-1]
    chosen: list[SampledStar] = []
    for index in order:
        star = sources[int(index)]
        x = float(star["x"])
        y = float(star["y"])
        if any(_same_star(x, y, kept) for kept in chosen):
            continue
        try:
            side = _dynamic_box_side(signal, star, segmap)
            origin_x, origin_y, cut = _cut_box(signal, x, y, side)
            sigma_x, sigma_y, _amplitude, gauss_x, gauss_y = _fit_gaussian(cut, side)
        except MeasureError:
            continue
        sigma = (sigma_x + sigma_y) / 2.0
        if sigma < _MIN_STAR_SIGMA:
            continue
        profile = radial_profile(cut, gauss_x, gauss_y)
        chosen.append(
            SampledStar(
                x=x,
                y=y,
                flux=float(star["flux"]),
                sigma=sigma,
                box_origin_x=origin_x,
                box_origin_y=origin_y,
                box_size=side,
                gauss_x=gauss_x,
                gauss_y=gauss_y,
                center_ratio=profile.ratio,
                ring_radius=profile.ring_radius,
                donut=profile.donut,
            )
        )
        if len(chosen) == _DONUT_SAMPLE:
            break
    return chosen


def _same_star(x: float, y: float, star: SampledStar) -> bool:
    half = star.box_size / 2.0
    return abs(x - star.x) <= half and abs(y - star.y) <= half


def recommend_focus(
    positions: Sequence[float],
    sigmas: Sequence[float],
) -> FocusRecommendation:
    x = np.asarray(positions, dtype=float)
    y = np.asarray(sigmas, dtype=float)
    if x.size == 0:
        raise MeasureError("No focus measurements to fit.")
    if x.size != y.size:
        raise MeasureError("Focus positions and sigmas do not match.")

    best = int(np.argmin(y))
    lowest_position = int(round(float(x[best])))
    lowest_sigma = float(y[best])

    if x.size < 3:
        return FocusRecommendation(
            position=lowest_position,
            sigma=lowest_sigma,
            curve_ok=False,
            message=(
                "Fewer than 3 points. Lowest measured sigma is "
                f"{lowest_sigma:.3f} at step {lowest_position}."
            ),
            curve=[],
        )

    center = float(np.mean(x))
    # sigma = a u^2 + b u + c, u = focus - mean(focus). Vertex at u = -b / (2a).
    quadratic = np.polyfit(x - center, y, 2)
    slope_coeff, linear_coeff, constant = (float(v) for v in quadratic)
    samples = _curve_samples(
        x,
        center,
        slope_coeff,
        linear_coeff,
        constant,
    )

    if slope_coeff <= 0:
        return FocusRecommendation(
            position=lowest_position,
            sigma=lowest_sigma,
            curve_ok=False,
            message=(
                "The fitted curve does not open upward. Lowest measured sigma is "
                f"{lowest_sigma:.3f} at step {lowest_position}."
            ),
            curve=samples,
        )

    vertex = center - linear_coeff / (2.0 * slope_coeff)
    if vertex < float(np.min(x)) or vertex > float(np.max(x)):
        return FocusRecommendation(
            position=lowest_position,
            sigma=lowest_sigma,
            curve_ok=False,
            message=(
                "The parabola minimum is outside the sweep. Lowest measured sigma is "
                f"{lowest_sigma:.3f} at step {lowest_position}."
            ),
            curve=samples,
        )

    position = int(round(vertex))
    sigma = slope_coeff * (position - center) ** 2
    sigma += linear_coeff * (position - center)
    sigma += constant
    return FocusRecommendation(
        position=position,
        sigma=float(sigma),
        curve_ok=True,
        message=f"Parabola minimum is at step {position}.",
        curve=samples,
    )


def _extract(
    image: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    data = np.ascontiguousarray(image, dtype=np.float32)
    if data.ndim != 2:
        raise MeasureError(NO_STAR_IN_IMAGE)
    data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
    try:
        background = sep.Background(data)
        signal = np.ascontiguousarray(data - background, dtype=np.float32)
        sources, segmap = sep.extract(
            signal,
            _SEP_THRESHOLD,
            err=background.globalrms,
            minarea=_SEP_MIN_AREA,
            segmentation_map=True,
        )
    except Exception as err:
        raise MeasureError(NO_STAR_IN_IMAGE) from err
    return signal, sources, segmap


def _dynamic_box_side(
    signal: np.ndarray,
    star: np.ndarray,
    segmap: np.ndarray,
) -> int:
    a = float(star["a"])
    b = float(star["b"])
    theta = float(star["theta"])
    if min(a, b) <= 0 or not np.isfinite(a + b + theta):
        raise MeasureError(NO_STAR_IN_IMAGE)

    scale = _light_scale(signal, star, segmap, a, b, theta)
    cos_t = float(np.cos(theta))
    sin_t = float(np.sin(theta))
    # Axis-aligned extents of the rotated ellipse. The square uses the larger one.
    half_x = scale * float(np.hypot(a * cos_t, b * sin_t))
    half_y = scale * float(np.hypot(a * sin_t, b * cos_t))
    half = int(np.ceil(max(half_x, half_y) + _BOX_PADDING_PX))
    return max(2 * half + 1, _MIN_DYNAMIC_BOX)


def _light_scale(
    signal: np.ndarray,
    star: np.ndarray,
    segmap: np.ndarray,
    a: float,
    b: float,
    theta: float,
) -> float:
    peak_y = int(star["ypeak"])
    peak_x = int(star["xpeak"])
    seg_id = int(segmap[peak_y, peak_x])
    mask_args: dict[str, np.ndarray | int] = {}
    if seg_id > 0:
        mask_args["segmap"] = segmap
        mask_args["seg_id"] = seg_id
    try:
        kronrad, _flag = sep.kron_radius(
            signal,
            float(star["x"]),
            float(star["y"]),
            a,
            b,
            theta,
            _KRON_WINDOW,
            **mask_args,
        )
    except Exception as err:
        raise MeasureError(NO_STAR_IN_IMAGE) from err

    kron = float(np.asarray(kronrad).reshape(-1)[0])
    if not np.isfinite(kron) or kron <= 0:
        return _KRON_MIN_SCALE
    return max(_KRON_FACTOR * kron, _KRON_MIN_SCALE)


def _check_shift(
    x: float,
    y: float,
    previous_center: tuple[float, float] | None,
) -> None:
    if previous_center is None:
        return
    shift = float(np.hypot(x - previous_center[0], y - previous_center[1]))
    if shift > MAX_STAR_SHIFT_PX:
        raise MeasureError(f"Star moved {shift:.0f} pixels since the previous frame.")


def _square_side(box_size: int | tuple[int, int]) -> int:
    if isinstance(box_size, tuple):
        if len(box_size) != 2 or box_size[0] != box_size[1]:
            raise MeasureError("The measurement box must be square.")
        side = box_size[0]
    else:
        side = box_size
    if isinstance(side, bool) or not isinstance(side, (int, np.integer)):
        raise MeasureError("The measurement box side must be a whole number of pixels.")
    if int(side) < 8:
        raise MeasureError("The measurement box must be at least 8 pixels on a side.")
    return int(side)


def _cut_box(
    signal: np.ndarray,
    x: float,
    y: float,
    box_size: int,
) -> tuple[int, int, np.ndarray]:
    half = box_size // 2
    origin_x = int(round(x)) - half
    origin_y = int(round(y)) - half
    height, width = signal.shape
    if (
        origin_x < 0
        or origin_y < 0
        or origin_x + box_size > width
        or origin_y + box_size > height
    ):
        raise MeasureError(
            "No star in the measurement box. "
            "The brightest star is too close to the edge of the image."
        )
    cut = np.ascontiguousarray(
        signal[origin_y : origin_y + box_size, origin_x : origin_x + box_size]
    )
    return origin_x, origin_y, cut


def _fit_gaussian(
    cut: np.ndarray,
    box_size: int,
) -> tuple[float, float, float, float, float]:
    try:
        background = sep.Background(cut)
        sources = sep.extract(
            cut,
            _SEP_THRESHOLD,
            err=background.globalrms,
            minarea=_SEP_MIN_AREA,
        )
    except Exception as err:
        raise MeasureError("No star in the measurement box.") from err
    if len(sources) == 0:
        raise MeasureError("No star in the measurement box.")

    star = sources[int(np.argmax(sources["flux"]))]
    model = models.Gaussian2D(
        amplitude=float(max(np.max(cut), 1.0)),
        x_mean=float(star["x"]),
        y_mean=float(star["y"]),
        x_stddev=float(max(star["a"], 1.0)),
        y_stddev=float(max(star["b"], 1.0)),
        theta=0.0,
    )
    model.theta.fixed = True
    model.amplitude.bounds = (0.0, None)
    model.x_mean.bounds = (0.0, box_size - 1.0)
    model.y_mean.bounds = (0.0, box_size - 1.0)
    model.x_stddev.bounds = (0.2, box_size / 2.0)
    model.y_stddev.bounds = (0.2, box_size / 2.0)

    yy, xx = np.mgrid[0:box_size, 0:box_size]
    try:
        fitted = fitting.TRFLSQFitter()(model, xx, yy, cut)
        sigma_x = abs(float(fitted.x_stddev.value))
        sigma_y = abs(float(fitted.y_stddev.value))
        amplitude = float(fitted.amplitude.value)
        gauss_x = float(fitted.x_mean.value)
        gauss_y = float(fitted.y_mean.value)
    except ImportError:
        raise
    except Exception as err:
        raise MeasureError("No star in the measurement box.") from err

    if (
        not np.isfinite(sigma_x)
        or not np.isfinite(sigma_y)
        or not np.isfinite(amplitude)
        or sigma_x <= 0
        or sigma_y <= 0
        or amplitude <= 0
    ):
        raise MeasureError("No star in the measurement box.")
    return sigma_x, sigma_y, amplitude, gauss_x, gauss_y


def _curve_samples(
    positions: np.ndarray,
    center: float,
    quadratic: float,
    linear: float,
    constant: float,
) -> list[tuple[float, float]]:
    xs = np.linspace(float(np.min(positions)), float(np.max(positions)), 40)
    ys = quadratic * (xs - center) ** 2 + linear * (xs - center) + constant
    return [(float(x), float(y)) for x, y in zip(xs, ys)]
