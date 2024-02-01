from dataclasses import dataclass, field
import json 
import numpy as np


@dataclass
class FocusSession():
    id: str = ""
    focuser_positons: list = field(default_factory=list)   # list of values
    fwhm_metrics: list = field(default_factory=list)   # list of values
    hfd_metrics: list = field(default_factory=list)   # list of dicts containing values for each method
    files: list = field(default_factory=list)
    
    fwhm_fit: np.ndarray = None
    hfd_fits: dict[np.ndarray] = field(default_factory=dict)
    
    predicted_min_fwhm: float = 0
    predicted_min_hfd: dict = field(default_factory=dict)

    def serialize(self):
        return {
            "id": self.id,
            "focuser_positons": self.focuser_positons,
            "fwhm_metrics": self.fwhm_metrics,
            "hfd_metrics": self.hfd_metrics,
            "files": self.files,
            "fwhm_fit": list(self.fwhm_fit) if self.fwhm_fit is not None else None,
            "hfd_fits": {method: list(fit) for method, fit in self.hfd_fits.items()} if self.hfd_fits is not None else None,
            "predicted_min_fwhm": self.predicted_min_fwhm,
            "predicted_min_hfd": self.predicted_min_hfd
        }
    