"""Training scaffolding for the cookedness battery.

Reusable drivers for fine-tuning / distilling model organisms. Currently the
only backend is Tinker (``battery.train.tinker``). All heavy dependencies
(``tinker``, ``tinker_cookbook``, ``torch``) are imported LAZILY inside the
entrypoints, so ``import battery.train`` stays light and does not require the
optional ``tinker`` extra.
"""
