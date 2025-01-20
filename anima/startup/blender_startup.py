import sys
import bpy
import inspect


def blender_startup_dir():
    return '/blender-4.' in sys.executable.lower()


if blender_startup_dir():
    import customs
else:
    import anima.startup.customs as customs


@bpy.app.handlers.persistent
def load_handlers(dummy):
    for name, obj in inspect.getmembers(customs):
        if inspect.isfunction(obj):
            bpy.app.driver_namespace[name] = obj


def register():
    print("Register:", __file__)

    load_handlers(None)
    bpy.app.handlers.load_post.append(load_handlers)


def unregister():
    bpy.app.handlers.load_post.remove(load_handlers)


if __name__ == "__main__":
    register()
