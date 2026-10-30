"""Brush shader stanzas and the .shader / .arena writers.

    from woplib import shaders as SH
    SH.configure('padfoo', 'wop_padfoo', 'Pretty Name')
    parts = [SH.lm('floor', steps='woodsteps'), SH.sky('env/fort-pad512', sun=(100, 52)), SH.nodraw_ns(), SH.jumppad(),
             SH.glass(), SH.water('water'), ML.model_shaders(), SH.levelshot_anim()]
    SH.write_shader(out_dir, parts)
    SH.write_arena(out_dir, 'ffa lps team ft syc_ffa')

Brush texture names in the .map are `<ns>/<name>` (NO textures/ prefix); shader names here are `textures/<ns>/<name>`.
"""
import os
from . import wopdata

CFG = {'ns': 'woplib', 'map': 'wop_x', 'longname': 'X'}


def configure(ns, mapname, longname):
    CFG.update(ns=ns, map=mapname, longname=longname)


def td(): return f'textures/{CFG["ns"]}'


def lm(name, steps=None, extra='', tex=None, stage='', editor=None):
    """plain lightmapped brush texture; steps = WoP footstep surfaceparm (woodsteps, sandsteps, softsteps,
    splashsteps, snowsteps, carpetsteps, latticesteps; needs -custinfoparms)"""
    t = tex or f'{td()}/{name}'
    s = f'{td()}/{name}\n{{\n\tqer_editorimage {editor or t}\n'
    if steps: s += f'\tsurfaceparm {steps}\n'
    s += extra
    s += ('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}\n'
          f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}}\n')
    return s + stage + '}\n\n'


def sign(name, **kw):
    """lightmapped sign/poster (no decals on it)"""
    return lm(name, extra='\tsurfaceparm nomarks\n' + kw.pop('extra', ''), **kw)


def sky(skyparms='env/fort-pad512', sun=(270, 50), sun_rgb=(1, 0.96, 0.88), sun_int=220, skylight=(40, 3),
        name='sky', editor=None, cloud=None):
    """sky shader. sun = (yaw toward the sun, elevation); 270 = the sun stands in the south. Custom cube:
    env/<ns>/name_rt|lf|bk|ft|up|dn (rt=+x, lf=-x, bk=+y, ft=-y). cloud = image for a scrolling cloud layer."""
    t = td()
    s = (f'{t}/{name}\n{{\n\tqer_editorimage {editor or skyparms + "_ft"}\n\tsurfaceparm noimpact\n\tsurfaceparm nolightmap\n'
         f'\tsurfaceparm sky\n\tq3map_sun {sun_rgb[0]:g} {sun_rgb[1]:g} {sun_rgb[2]:g} {sun_int:g} {sun[0]:g} {sun[1]:g}\n'
         f'\tq3map_skylight {skylight[0]:g} {skylight[1]:g}\n\tskyparms {skyparms} {"512" if cloud else "-"} -\n')
    if cloud:
        s += (f'\t{{\n\t\tmap {cloud}\n\t\tblendFunc GL_ONE GL_ONE\n\t\ttcMod scale 3 3\n\t\ttcMod scroll 0.006 0.002\n'
              f'\t\trgbGen identityLighting\n\t}}\n')
    return s + '}\n\n'


def slick(name, steps=None, glint=True, editor=None):
    """lightmapped slippery floor (ice, frost, spilled oil): surfaceparm slick removes ground friction, so players
    slide. Keep slick patches away from deadly edges and pad landings (bots slide off), and give the edge botclip.
    glint adds a slow additive sparkle stage."""
    t = f'{td()}/{name}'
    stage = (f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.08 0.06 0 0.3\n'
             f'\t\ttcMod scroll 0.01 0.006\n\t}}\n') if glint else ''
    return lm(name, steps=steps, extra='\tsurfaceparm slick\n', stage=stage, editor=editor)


def nodraw_ns(name='nodraw_ns'):
    """invisible nonsolid brush (movers' tiny brush for model2, decal backs). WoP's common/nodrawnonsolid also works."""
    t = f'{td()}/{name}'
    return (f'{t}\n{{\n\tqer_editorimage {t}\n\tqer_trans 0.4\n\tsurfaceparm nodraw\n\tsurfaceparm nonsolid\n'
            f'\tsurfaceparm trans\n\tsurfaceparm nomarks\n\tsurfaceparm noimpact\n\tsurfaceparm nolightmap\n}}\n\n')


def glass(name='glass', rgb='0.10 0.12 0.13', env=None, solid=True, shadow=True):
    """glass that reads clear (GL_ONE GL_ONE + dim const; GL_DST_COLOR GL_ONE renders white). alphashadow gives
    grid shadows from glazing; shadow=False lets light straight through (glass shelves: with alphashadow an image
    without an alpha channel shadows like a solid slab). env: image for a reflection stage (models/<ns>/env)."""
    t = f'{td()}/{name}'
    s = (f'{t}\n{{\n\tqer_editorimage {t}\n\tqer_trans 0.4\n\tsurfaceparm trans\n\tsurfaceparm nolightmap\n'
         f'\tsurfaceparm nomarks\n' + ('\tsurfaceparm alphashadow\n' if shadow else '') + ('' if solid else '\tsurfaceparm nonsolid\n') +
         f'\tcull none\n\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( {rgb} )\n\t}}\n')
    if env:
        s += f'\t{{\n\t\tmap {env}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen const ( 0.12 0.12 0.13 )\n\t\ttcGen environment\n\t}}\n'
    return s + '}\n\n'


def water(name='water', rgb=(0.3, 0.55, 0.65), alpha=0.55, fog=None, nodraw_name=None):
    """water surface (draw only the top faces of the carved water brushes; give internal faces nodraw_name).
    fog = (r, g, b, dist) adds fogparms for murky water."""
    t = f'{td()}/{name}'
    s = (f'{t}\n{{\n\tqer_editorimage {t}\n\tqer_trans 0.5\n\tsurfaceparm water\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n'
         f'\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n\tcull none\n\tq3map_globalTexture\n'
         f'\tdeformVertexes wave 128 sin 0 2 0 0.4\n')
    if fog: s += f'\tfogparms ( {fog[0]:g} {fog[1]:g} {fog[2]:g} ) {fog[3]:g}\n'
    s += (f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA\n\t\trgbGen const ( {rgb[0]:g} {rgb[1]:g} {rgb[2]:g} )\n'
          f'\t\talphaGen const {alpha:g}\n\t\ttcMod scroll 0.02 0.01\n\t\ttcMod turb 0 0.05 0 0.2\n\t}}\n}}\n\n')
    nn = nodraw_name or name + '_nd'
    s += (f'{td()}/{nn}\n{{\n\tqer_editorimage {t}\n\tqer_trans 0.3\n\tsurfaceparm water\n\tsurfaceparm trans\n'
          f'\tsurfaceparm nonsolid\n\tsurfaceparm nodraw\n\tsurfaceparm nomarks\n\tsurfaceparm nolightmap\n}}\n\n')
    return s


def fog(name='fog', rgb=(0.16, 0.40, 0.56), dist=4800, top_visible=True):
    """fog volume (put it on all 6 faces of one brush). q3map_fogDir ( 0 0 -1 ) makes the top face the visible
    side (the parentheses are required). Pass --shaders to audit_map/sightlines so the fog brush is not a solid."""
    t = f'{td()}/{name}'
    s = (f'{t}\n{{\n\tqer_editorimage {t}\n\tqer_trans 0.3\n\tsurfaceparm fog\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n'
         f'\tsurfaceparm nolightmap\n\tfogparms ( {rgb[0]:g} {rgb[1]:g} {rgb[2]:g} ) {dist:g}\n')
    if top_visible: s += '\tq3map_fogDir ( 0 0 -1 )\n'
    return s + '}\n\n'


def neon(name, rgb=(1.0, 0.35, 0.7), light=300):
    """glowing neon (put it on a DARK backing board: additive neon on a bright wall washes out)"""
    t = f'{td()}/{name}'
    return (f'{t}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n'
            f'\tq3map_surfacelight {light}\n\tq3map_lightRGB {rgb[0]:.2f} {rgb[1]:.2f} {rgb[2]:.2f}\n\tq3map_lightSubdivide 64\n'
            f'\t{{\n\t\tmap {t}\n\t\trgbGen wave sin 0.9 0.1 0 0.5\n\t}}\n}}\n\n')


def jumppad(name='jumppad', rgb=(1, 0.6, 0.8)):
    """lightmapped pad top with a pulsing, turning additive stage (texture written by kit.write_kit_textures)"""
    t = f'{td()}/{name}'
    stage = f'\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n\t\trgbGen wave sin 0.2 0.2 0 0.8\n\t\ttcMod rotate 30\n\t}}\n'
    return lm(name, extra=f'\tq3map_surfacelight 60\n\tq3map_lightRGB {rgb[0]:g} {rgb[1]:g} {rgb[2]:g}\n\tq3map_lightSubdivide 128\n',
              stage=stage)


def pulse(name, phase=0.0, freq=1.0):
    """pulsing insert/light decal: 1u nonsolid decal brush, additive square wave (use 4 phases for a chase)"""
    t = f'{td()}/{name}'
    return (f'{t}\n{{\n\tqer_editorimage {t}\n\tsurfaceparm nolightmap\n\tsurfaceparm nonsolid\n\tsurfaceparm trans\n'
            f'\tsurfaceparm nomarks\n\tpolygonOffset\n\t{{\n\t\tmap {t}\n\t\tblendFunc GL_ONE GL_ONE\n'
            f'\t\trgbGen wave square 0.5 0.5 {phase:g} {freq:g}\n\t}}\n}}\n\n')


def levelshot_anim():
    m = CFG['map']
    return (f'levelshots/{m}B\n{{\n\tnomipmaps\n\t{{\n\t\tanimmap 0.5 levelshots/{m}B1 levelshots/{m}B2 levelshots/{m}B3\n\t}}\n}}\n\n')


def write_shader(out_dir, parts, header=None):
    path = os.path.join(out_dir, 'scripts', CFG['ns'] + '.shader')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    txt = header or f'// {CFG["ns"]}.shader - {CFG["longname"]} (generated with wop_tools/woplib)\n\n'
    txt += ''.join(parts)
    names = [l.strip() for l in txt.splitlines() if l and not l[0].isspace() and l.strip() not in ('{', '}') and not l.startswith('//')]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup: raise ValueError(f'duplicate shader names: {dup[:8]}')
    for n in names:
        if n != n.lower() and not n.startswith('levelshots/'): raise ValueError(f'shader names must be lower case (case matters in pk3s on Linux): {n}')
    open(path, 'w').write(txt)
    return path


def write_arena(out_dir, types='ffa lps team ft syc_ffa', ents=None):
    """scripts/<map>.arena. types are checked against WoP's tokens; with ents (list of classnames in the map),
    ctl / 1lc are checked against the lollies they need."""
    tt = types.split()
    bad = [t for t in tt if t not in wopdata.ARENA_TYPES]
    if bad: raise ValueError(f'unknown arena types {bad}; valid: {" ".join(wopdata.ARENA_TYPES)}')
    if ents is not None:
        for t in tt:
            for need in wopdata.ARENA_NEEDS.get(t, ()):
                if need not in ents: raise ValueError(f'arena type {t} needs a {need} in the map')
    path = os.path.join(out_dir, 'scripts', CFG['map'] + '.arena')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w').write('{\n\tmap      "%s"\n\tlongname "%s"\n\ttype     "%s"\n}\n' % (CFG['map'], CFG['longname'], ' '.join(tt)))
    return path
