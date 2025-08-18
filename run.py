from anima.utils.blender import BlenderProcess


def run():
    bp = BlenderProcess()
    bp.start()
    bp.monitor()


if __name__ == "__main__":
    run()
