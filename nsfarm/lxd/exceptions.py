"""NSFamrm.LXD specific exceptions.
"""


class NSFarmLXDException(Exception):
    """Generic failure in NSFarm's LXD code.
    """


class LXDImageUndefined(NSFarmLXDException):
    """Image with given name is not defined by appropriate files (in imgs directory in repository root).
    """

    def __init__(self, img_name, file_path):
        super().__init__(f"There seems to be no file describing image '{img_name}': {file_path}")


class LXDImageUnknowParent(NSFarmLXDException):
    """This is raised when image defining script specifies invalid or none parent name.
    """

    def __init__(self, img_name, parent):
        super().__init__(f"The image '{img_name}' has parent from unknown source: {parent}")
