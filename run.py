from anima.utils.blender_utils import BlenderProcess


def run():
    BlenderProcess().initialize()\
                    .monitor()


if __name__ == '__main__':
    run()
