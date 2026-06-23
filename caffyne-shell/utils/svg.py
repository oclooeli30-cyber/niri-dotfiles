from fabric.utils import get_relative_path

def get_svg_path(svg_name):
    return get_relative_path("../svgs/" + svg_name + ".svg")