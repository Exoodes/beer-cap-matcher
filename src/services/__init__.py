"""Application services package.

Modules are imported directly (e.g. ``src.services.beer_cap_facade``) so that
the ML services, which load torch, are only imported when matching is enabled.
"""
