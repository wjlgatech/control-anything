"""The lean core: stdlib + pyyaml only, enforced by ``tools/layers.py``.

Core never imports an addon. New capability arrives as an addon declared in
``data/addons.yml``, reached through a seam — never by a hard import from here.
"""
