from anima.utils.blender import BlenderProcess


def run():
    BlenderProcess().start().monitor()


if __name__ == "__main__":
    run()
