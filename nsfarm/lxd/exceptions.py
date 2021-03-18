"""NSFamrm.LXD specific exceptions.
"""


class NSFarmLXDError(Exception):
    """Generic failure in NSFarm's LXD code.
    """


class LXDImageUndefinedError(NSFarmLXDError):
    """Image with given name is not defined by appropriate files (in imgs directory in repository root).
    """

    def __init__(self, img_name, file_path):
        super().__init__(f"There seems to be no file describing image '{img_name}': {file_path}")


class LXDImageParentError(NSFarmLXDError):
    """This is raised when image defining script specifies invalid or none parent name.
    """

    def __init__(self, img_name, parent):
        super().__init__(f"The image '{img_name}' has parent from unknown source: {parent}")


class LXDImageParameterError(NSFarmLXDError):
    """This is raised when image defining script specifies invalid image parameter.
    """

    def __init__(self, img_name, parameter):
        super().__init__(f"The image '{img_name}' has unknown parameter: {parameter}")


class LXDDeviceError(NSFarmLXDError):
    """Image specifies device that wasn't located in device map and thus is not available or there was any other problem
    to get full device specification.
    """

    def __init__(self, device):
        super().__init__(f"The device can't be initialized: {device}")
