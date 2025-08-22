import os


root_dir = os.path.dirname(os.path.abspath(__file__))


def get_template_path(name):
    root_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(root_dir, name)
