# rutabaga: an OpenGL widget toolkit
# Copyright (c) 2013-2018 William Light.
# All rights reserved.
#
# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# For more information, please refer to <http://unlicense.org/>

from rutabaga_css.asset import *

all = [
    "RutabagaFontFace",
    "RutabagaEmbeddedFontAsset"]

class RutabagaEmbeddedFontAsset(RutabagaEmbeddedAsset):
    def __init__(self, path, asset_var, descriptor_var):
        RutabagaEmbeddedAsset.__init__(self, path, asset_var)
        self.descriptor_var = descriptor_var
        self.refcount = 0

class RutabagaFontFace(object):
    def __init__(self, family):
        from itertools import repeat

        self.family = family
        self.weights = {"normal": None}

    def add_weight(self, stylesheet, weight_name, src):
        cvar = sanitize_c_variable(self.family + "_" + weight_name)
        asset = RutabagaEmbeddedFontAsset(src, cvar.upper(), cvar.lower())

        self.weights[weight_name] = asset
        stylesheet.embedded_assets.append(asset)

    def use_weight(self, weight_name=None):
        w = self.weights[weight_name or 'normal']
        w.refcount += 1
        return w

    c_weight_repr = """\
static const struct rtb_style_font_face {def_var} = {{
\t.family = "{family}",
\t.weight = "{weight}",
\t.loaded = 1,
\t.location = RTB_ASSET_EMBEDDED,
\t.compression = RTB_ASSET_UNCOMPRESSED,
\t.buffer.allocated = 0,
\t.buffer.data = {asset_var},
\t.buffer.size = sizeof({asset_var})
}};"""

    def c_repr(self):
        return "\n\n".join([self.c_weight_repr.format(
            family=self.family,
            weight=weight,
            def_var=self.weights[weight].descriptor_var,
            asset_var=self.weights[weight].asset_var)
                for weight in self.weights
                    if self.weights[weight].refcount > 0])
