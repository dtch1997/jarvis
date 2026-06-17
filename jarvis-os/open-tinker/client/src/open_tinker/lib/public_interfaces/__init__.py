"""``tinker.lib.public_interfaces`` compatibility surface.

The cookbook imports ``APIFuture`` and ``RestClient`` from here. We re-export the
canonical implementations (``APIFuture`` lives in ``open_tinker._futures``;
clients live in ``open_tinker.clients``) so both the flat ``tinker.X`` names and
the ``tinker.lib.public_interfaces.X`` paths resolve to the same objects.
"""

from ..._futures import APIFuture
from ...clients.sampling_client import SamplingClient
from ...clients.service_client import ServiceClient
from ...clients.training_client import TrainingClient
from .rest_client import RestClient

__all__ = ["APIFuture", "RestClient", "ServiceClient", "TrainingClient", "SamplingClient"]
