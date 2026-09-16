"""podcaster — a topic goes in, a podcast episode you would actually listen to
comes out.

Three passes, each a seam you can drive on its own:

* **research** (:mod:`podcaster.research`) — pick one *angle*, fan out one
  web-researched question per beat, synthesize a brief with sources attached.
* **write** (:mod:`podcaster.script`) — draft a spoken-word script and gate it on
  mechanical listenability checks (:mod:`podcaster.style`), feeding failures back
  into a rewrite. The gate is the difference between a script and an essay
  read aloud.
* **narrate** (:mod:`podcaster.voice`, :mod:`podcaster.audio`) — normalize prose
  into speakable text, synthesize with a local CPU model (Piper), master to a
  tagged MP3.

The whole thing is one declared :func:`podcaster.pipeline.make_episode` flow; the
LLM, the TTS engine and object storage are all injectable seams, so the pipeline
is testable end-to-end offline.
"""

from .models import (Beat, Brief, Episode, Finding, Plan, Question, Script,
                     Segment, read_json, write_json)
from .pipeline import EpisodeSpec, make_episode, narrate_script
from .style import StyleReport, audit, check
from .voice import DEFAULT_VOICE, PiperBackend, SineBackend, installed_voices

__all__ = [
    "Beat", "Brief", "Episode", "Finding", "Plan", "Question", "Script", "Segment",
    "read_json", "write_json",
    "EpisodeSpec", "make_episode", "narrate_script",
    "StyleReport", "audit", "check",
    "DEFAULT_VOICE", "PiperBackend", "SineBackend", "installed_voices",
]
__version__ = "0.1.0"
