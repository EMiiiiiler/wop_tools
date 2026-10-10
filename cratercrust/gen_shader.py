#!/usr/bin/env python3
"""Writes scripts/cratercrust.shader"""
import sys, os
OUT = sys.argv[1] if len(sys.argv) > 1 else 'out'
os.makedirs(os.path.join(OUT, 'scripts'), exist_ok=True)
P = 'textures/cratercrust/'
out = ['// Crater Crust (wop_cratercrust) - shaders', '// compile with -custinfoparms (WoP footstep surfaceparms)', '']


def lm(name, ext='jpg', parms=(), extra=()):
    """standard lightmapped shader with surfaceparms (for footsteps)"""
    out.append(P + name)
    out.append('{')
    out.append('\tqer_editorimage %s%s.%s' % (P, name, ext))
    for p in parms: out.append('\tsurfaceparm ' + p)
    for e in extra: out.append('\t' + e)
    out.append('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}')
    out.append('\t{\n\t\tmap %s%s.%s\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}' % (P, name, ext))
    out.append('}\n')


def glow(name, light, parms=(), pulse=None, extra=(), ext='jpg', subdiv=64):
    out.append(P + name)
    out.append('{')
    out.append('\tqer_editorimage %s%s.%s' % (P, name, ext))
    out.append('\tq3map_surfacelight %d' % light)
    out.append('\tq3map_lightSubdivide %d' % subdiv)
    out.append('\tsurfaceparm nomarks')
    for p in parms: out.append('\tsurfaceparm ' + p)
    for e in extra: out.append('\t' + e)
    out.append('\t{\n\t\tmap $lightmap\n\t\trgbGen identity\n\t}')
    out.append('\t{\n\t\tmap %s%s.%s\n\t\tblendFunc GL_DST_COLOR GL_ZERO\n\t\trgbGen identity\n\t}' % (P, name, ext))
    rg = 'rgbGen wave sin %s' % pulse if pulse else 'rgbGen identity'
    out.append('\t{\n\t\tmap %s%s.%s\n\t\tblendFunc GL_ONE GL_ONE\n\t\t%s\n\t}' % (P, name, ext, rg))
    out.append('}\n')


# ---- sky (night, moon light from the moon side of the box)
out.append('''textures/cratercrust/cc_sky
{
	qer_editorimage env/cratercrust/cc_sky_ft.jpg
	surfaceparm noimpact
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm sky
	q3map_sunExt 0.62 0.68 1.0 110 70 40 3 16
	q3map_skyLight 40 3
	skyparms env/cratercrust/cc_sky - -
}
''')

# ---- footstep / material shaders
for n in ('cc_carpet',): lm(n, parms=('carpetsteps',))
for n in ('cc_wood', 'cc_crate', 'cc_fence', 'cc_cuttingboard', 'cc_pizzabox'): lm(n, parms=('woodsteps',))
for n in ('cc_vinyl', 'cc_foam', 'cc_grass', 'cc_rubber'): lm(n, parms=('softsteps',))
for n in ('cc_roof',): lm(n, parms=('sandsteps',))
for n in ('cc_steel', 'cc_duct', 'cc_truss', 'cc_shelf', 'cc_shelf_side', 'cc_van', 'cc_van_floor', 'cc_van_cabside',
          'cc_van_grille', 'cc_van_windshield', 'cc_dumpster', 'cc_ac', 'cc_ac_top', 'cc_counter_top', 'cc_foil',
          'cc_lander', 'cc_cab_top', 'cc_claw_base', 'cc_sign_back', 'cc_solar', 'cc_skylight', 'cc_tank'):
    lm(n, parms=('metalsteps',))
lm('cc_van_logo', parms=('metalsteps',))

# ---- glowing surfaces
glow('cc_neon_cyan', 250, pulse='0.85 0.15 0 0.4')
glow('cc_neon_magenta', 250, pulse='0.85 0.15 0.3 0.4')
glow('cc_neon_yellow', 200, pulse='0.85 0.15 0.6 0.4')
for n in ('cc_marquee', 'cc_marquee2', 'cc_marquee3'): glow(n, 120, parms=('metalsteps',))
glow('cc_lamp_light', 2500, subdiv=32)
glow('cc_sign', 160, parms=('metalsteps',), subdiv=128)
glow('cc_jumppad', 400, parms=('metalsteps',), pulse='0.7 0.3 0 1.2', subdiv=32)
glow('cc_pad_side', 150, parms=('metalsteps',))
glow('cc_coals', 900, pulse='0.75 0.25 0 0.3', subdiv=32)

# arcade screens: glowing image + scrolling scanlines
for n in ('cc_screen', 'cc_screen2', 'cc_screen3'):
    out.append('''textures/cratercrust/%s
{
	qer_editorimage textures/cratercrust/%s.jpg
	q3map_surfacelight 150
	q3map_lightSubdivide 64
	surfaceparm nomarks
	surfaceparm metalsteps
	{
		map textures/cratercrust/%s.jpg
		rgbGen wave sin 0.9 0.1 0 2
	}
	{
		map textures/cratercrust/cc_scanlines.jpg
		blendFunc GL_ONE GL_ONE
		tcMod scale 4 4
		tcMod scroll 0 0.5
		rgbGen identity
	}
}
''' % (n, n, n))

# glass (solid, translucent)
out.append('''textures/cratercrust/cc_glass
{
	qer_editorimage textures/cratercrust/cc_glass.tga
	qer_trans 0.4
	surfaceparm trans
	surfaceparm nolightmap
	surfaceparm nomarks
	cull none
	{
		map textures/cratercrust/cc_glass.tga
		blendFunc blend
		rgbGen identity
	}
}
''')

# grate (alpha tested, solid)
out.append('''textures/cratercrust/cc_grate
{
	qer_editorimage textures/cratercrust/cc_grate.tga
	qer_alphaFunc gequal 0.5
	surfaceparm trans
	surfaceparm alphashadow
	surfaceparm nomarks
	surfaceparm latticesteps
	cull none
	nopicmip
	{
		map textures/cratercrust/cc_grate.tga
		alphaFunc GE128
		depthWrite
		rgbGen identity
	}
	{
		map $lightmap
		blendFunc GL_DST_COLOR GL_ZERO
		depthFunc equal
		rgbGen identity
	}
}
''')

# sink water
out.append('''textures/cratercrust/cc_water
{
	qer_editorimage textures/cratercrust/cc_water.jpg
	qer_trans 0.5
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm splashsteps
	cull none
	tessSize 64
	deformVertexes wave 64 sin 0 1 0 0.4
	{
		map textures/cratercrust/cc_water.jpg
		blendFunc GL_DST_COLOR GL_ONE
		tcMod scroll 0.03 0.02
		rgbGen identity
	}
	{
		map textures/cratercrust/cc_water.jpg
		blendFunc GL_ONE GL_SRC_COLOR
		tcMod scale 0.5 0.5
		tcMod scroll -0.02 0.01
		rgbGen identity
	}
}
''')

# ball pit: swim-able "liquid" of plastic balls, fog hides what's on the bottom
out.append('''textures/cratercrust/cc_ballpit
{
	qer_editorimage textures/cratercrust/cc_ballpit.tga
	qer_trans 0.6
	surfaceparm trans
	surfaceparm nonsolid
	surfaceparm water
	surfaceparm fog
	surfaceparm nolightmap
	surfaceparm nomarks
	surfaceparm softsteps
	fogparms ( 0.55 0.25 0.65 ) 160
	q3map_fogDir ( 0 0 -1 )
	cull none
	deformVertexes wave 100 sin 0 2 0 0.3
	{
		map textures/cratercrust/cc_ballpit.tga
		blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		alphaGen const 0.92
		tcMod scale 2 2
		rgbGen identity
	}
}
''')

# parking line decal (sits on a 1u nodraw brush)
out.append('''textures/cratercrust/cc_lotline
{
	qer_editorimage textures/cratercrust/cc_lotline.tga
	surfaceparm nomarks
	{
		map $lightmap
		rgbGen identity
	}
	{
		map textures/cratercrust/cc_lotline.tga
		blendFunc GL_DST_COLOR GL_ZERO
		rgbGen identity
	}
}
''')

open(os.path.join(OUT, 'scripts/cratercrust.shader'), 'w').write('\n'.join(out))
print('shader written,', sum(1 for l in out if l.startswith('textures/')), 'shaders')
