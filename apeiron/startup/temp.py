from apeiron.general import driver_callable


@driver_callable
def halves(x):
    return 0.5 * x


def double(x):
    return 2.0 * x


class test:
    @staticmethod
    @driver_callable
    def method1(x):
        pass

    @driver_callable
    def method2(x):
        pass

    @staticmethod
    def method3(x):
        pass
