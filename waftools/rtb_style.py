#!/usr/bin/env python

from __future__ import print_function

from waflib.Configure import conf

from rutabaga_css import RutabagaStylesheet
from rutabaga_css.asset import *

from targa import *

def matches_extension(ext):
    from os.path import splitext
    return lambda i: splitext(i.name)[1] == ext

def do_css2c(task):
    var_name = "default_style"

    stylesheet = task.inputs[0].rtb_stylesheet

    output_file = lambda ext:\
        tuple(filter(matches_extension(ext), task.outputs))[0]

    output_file(".h").write(
        copyright + css2c_prelude
        + ("extern const struct rtb_style {var_name}[];\n"
           "extern const size_t {var_name}_size;\n"
           "extern const size_t {var_name}_fonts;\n").format(var_name=var_name))

    output_file(".c").write(
        copyright + css2c_prelude
        + stylesheet.c_prelude() + "\n\n"
        + "const struct rtb_style {var_name}[] = ".format(var_name=var_name)
        + stylesheet.c_repr(var_name)
        + "\n\nconst size_t {var_name}_size = sizeof({var_name});".format(var_name=var_name)
        + "\nconst size_t {var_name}_fonts = {fonts_used};".format(var_name=var_name, fonts_used = stylesheet.fonts_used))

####
# bin2c
####

def bin2c(binary, line_wrap=79, line_start=''):
    from math import floor

    hexesc = "0x{0:02X}"
    bytes_per_line = int(floor(line_wrap / len(hexesc.format(0) + ", ")))

    # from http://stackoverflow.com/questions/760753#760857
    def batch_gen(data, batch_size):
        for i in range(0, len(data), batch_size):
            yield data[i:i+batch_size]

    # py2/py3 compat
    chr_val = lambda x: ord(x[0]) if isinstance(x, str) else x

    return ",\n".join([
        line_start + ", ".join([hexesc.format(chr_val(byte)) for byte in line])
            for line in batch_gen(binary, bytes_per_line)])

def write_bin2c(header, data_file, data, var):
    header.write(
        copyright + bin2h_prelude
        + "extern const uint8_t {0}[{1}];".format(var, len(data)))

    data_file.write(
        copyright + bin2h_prelude
        + '#include "{0}"\n\n'.format(header.abspath())
        + "const uint8_t {0}[{1}] = {{\n".format(var, len(data))
        + bin2c(data, line_wrap=71, line_start='\t')
        + "\n};")

####
# img2c
####

def img2c_task(task):
    img = task.inputs[0].img
    c_var = task.inputs[0].asset_var

    output_file = lambda ext:\
        tuple(filter(matches_extension(ext), task.outputs))[0]

    write_bin2c(
        data_file=output_file(".c"),
        header=output_file(".h"),
        data=img.data,
        var=c_var)

def img2c_rule(bld, asset, src):
    node = bld.path.find_resource(src)

    img = TargaImage()
    img.from_bytes(node.read(flags="rb"))

    node.asset_var = asset.asset_var
    node.img = img

    asset.prop.width  = img.width
    asset.prop.height = img.height

    bld(
        rule=img2c_task,
        source=node,
        target=[src + ".h", src + ".c"],
        export_includes=".",
        update_outputs=True)

####
# font2c
####

def font2c_task(task):
    c_var = task.inputs[0].asset_var
    data = task.inputs[0].read(flags="rb")

    output_file = lambda ext:\
        tuple(filter(matches_extension(ext), task.outputs))[0]

    write_bin2c(
        data_file=output_file(".c"),
        header=output_file(".h"),
        data=data,
        var=c_var)

def font2c_rule(bld, asset, src):
    node = bld.path.find_resource(src)
    node.asset_var = asset.asset_var

    bld(
        rule=font2c_task,
        source=node,
        target=[src + ".h", src + ".c"],
        export_includes=".",
        update_outputs=True)

####
# css loader
####

def process_embedded_assets(bld, style_name, css):
    from rutabaga_css.properties.texture import RutabagaEmbeddedTextureAsset
    from rutabaga_css.font import RutabagaEmbeddedFontAsset

    sources = []

    for asset in css.embedded_assets:
        path  = "{0}/{1}".format(style_name, asset.path)

        if type(asset) == RutabagaEmbeddedTextureAsset:
            img2c_rule(bld, asset, path)

        elif type(asset) == RutabagaEmbeddedFontAsset:
            font2c_rule(bld, asset, path)

        else:
            print("???", type(asset))

        asset.header_path = "styles/{0}.h".format(path)
        sources.append(path + ".c")

    return sources

@conf
def rtb_style(bld, style_name, **kwargs):
    """Parses a CSS file and generates build rules for embedding assets."""

    css_path = "{0}/style.css".format(style_name)
    css_node = bld.path.find_resource(css_path)

    css = RutabagaStylesheet(css_node, autoparse=True)
    css_node.rtb_stylesheet = css

    asset_stlib_sources = process_embedded_assets(bld, style_name, css)

    for asset in css.external_assets:
        # transform external asset paths into absolute paths
        path = "{0}/{1}".format(style_name, asset.path)
        node = bld.path.find_resource(path)
        asset.path = node.abspath()

    bld(
        rule=do_css2c,
        source=css_node,
        target=["{0}/style.{1}".format(style_name, ext)
            for ext in ['c', 'h']],
        update_outputs=True)

    bld.stlib(
        source = asset_stlib_sources
            + ["{0}/style.c".format(style_name)],
        depends_on=asset_stlib_sources,
        includes=['..'],
        use=[
            'public',
            'private',
            'LIBUV'],
        cflags=bld.env['CFLAGS_cshlib'],
        **kwargs)

####
# some blocks of text
####

copyright = """\
/**
 * rutabaga: an OpenGL widget toolkit
 * Copyright (c) 2013-2018 William Light.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
 * ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

"""

css2c_prelude = """\
/**
 * this is an autogenerated file.
 * you probably don't want to edit this.
 */

#include <rutabaga/rutabaga.h>
#include <rutabaga/element.h>
#include <rutabaga/style.h>

"""

bin2h_prelude = """\
/**
 * this is an autogenerated file.
 * you probably don't want to edit this.
 */

#include <stdint.h>

"""
