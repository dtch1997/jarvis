#!/usr/bin/env python3
"""Build index.html for the 'Waking the Fly Brain' progress artifact.

Inlines figures + demo videos (base64) from repos/fly-api into
template.html. Rerun after updating assets or template; publish index.html
with the Artifact tool passing the existing url (see INDEX.md row).
"""
import base64
from pathlib import Path

HERE = Path(__file__).resolve().parent
p = HERE
while p != p.parent and not (p / 'repos' / 'fly-api' / 'media').exists():
    p = p.parent
SRC = p / 'repos' / 'fly-api'
assert (SRC / 'media').exists(), f'fly-api assets not found walking up from {HERE}'

def b64(rel, mime):
    return f'data:{mime};base64,' + base64.b64encode((SRC / rel).read_bytes()).decode()

ASSETS = {
    'FIG_DOSE':  b64('figures/a3_dose_response.png', 'image/png'),
    'FIG_SPEC':  b64('figures/a2_specificity.png', 'image/png'),
    'POSTER_B1': b64('figures/b1_frame.png', 'image/png'),
    'POSTER_B2': b64('figures/b2_frame.png', 'image/png'),
    'VID_WALK':  b64('media/b1_walking.mp4', 'video/mp4'),
    'VID_TAXIS': b64('media/b2_taxis_with_retina.mp4', 'video/mp4'),
    'FIG_ACQ':   b64('experiments/learning/figures/m1_acquisition.png', 'image/png'),
    'FIG_TRACE': b64('experiments/learning/figures/m3_generalization_trace.png', 'image/png'),
    'VID_NAV':   b64('media/nav_side_by_side.mp4', 'video/mp4'),
    'FIG_NAV':   b64('experiments/navigation/figures/n1_trajectories.png', 'image/png'),
}

out = (HERE / 'template.html').read_text()
missing = [k for k in ASSETS if '{{' + k + '}}' not in out]
assert not missing, f'template lacks placeholders: {missing}'
for k, v in ASSETS.items():
    out = out.replace('{{' + k + '}}', v)
assert '{{' not in out, 'unreplaced placeholder left in output'
(HERE / 'index.html').write_text(out)
print('built', HERE / 'index.html', f'{len(out)/1e6:.2f} MB')
