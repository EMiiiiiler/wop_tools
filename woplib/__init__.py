"""woplib - shared building blocks for World of Padman map generators.

    padmath  jump pad maths (AimAtTarget, target placement, flight time, bspc limits)
    kit      MapKit: a wopmap.Map plus placement/occupancy, items, pads, movers, secrets, routes, spot export
    models   custom MD3/IQM model + procedural texture helpers and the model shader writer
    shaders  brush shader stanzas (lightmapped, sky, glass, water, fog, neon, jump pad), .shader and .arena writers
    wopdata  WoP facts: entity classnames, bot weapon weights, arena game types, sounds known to exist

New maps: `python3 newmap.py wop_padfoo "Pretty Name"` scaffolds a folder that uses all of this.
"""
