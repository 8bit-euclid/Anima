import bpy
import inspect
import customs


@bpy.app.handlers.persistent
def load_handlers(dummy):
    for name, obj in inspect.getmembers(customs):
        bpy.app.driver_namespace[name] = obj


def register():
    print("Register:", __file__)

    load_handlers(None)
    bpy.app.handlers.load_post.append(load_handlers)


def unregister():
    bpy.app.handlers.load_post.remove(load_handlers)


if __name__ == "__main__":
    register()
