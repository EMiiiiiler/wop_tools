"""revolve_grid (surface of revolution with holes) borrowed from padshroom/shroom_models.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'padshroom'))
from shroom_models import revolve_grid  # noqa: F401
