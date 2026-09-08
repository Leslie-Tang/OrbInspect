"""Shared semantic colors for the approved manuscript figure family."""

TEAL = '#3F91A6'
# Slightly stronger than the schematic background, retaining band visibility
# at the existing 0.55 opacity and single-column print size.
TEAL_LIGHT = '#B7D7DE'
PURPLE = '#8771AA'
ONE_STEP_COLOR = '#B6A5CE'
SLATE = '#303E44'
ORANGE = '#E97900'
GREEN = '#27A27F'
ALERT = '#C30000'
GREY = '#647687'
LIGHT_GREY = '#DDDDDD'
BLACK = '#000000'

# Legacy vector colors are mapped by scientific role, not by one global swap.
DEPTH_REPLACEMENTS = {
    '#587e92': TEAL, '#750014': SLATE,
    '#6b7280': GREY, '#1e293b': BLACK,
}
ROUTE_REPLACEMENTS = {
    '#750014': TEAL, '#587e92': PURPLE, '#7f3f98': ORANGE,
    '#37a537': GREEN, '#e3ccd0': LIGHT_GREY,
    '#6b7280': GREY, '#1e293b': BLACK,
}
