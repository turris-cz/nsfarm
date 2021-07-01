"""Implementation of varous helper expected conditions.
"""


class element_has_class(object):
    """An expectation for checking that an element has a particular css class.

    locator - used to find the element
    invert - invert the check
    returns the WebElement once it has the particular css class
    """

    def __init__(self, locator, cls, invert=False):
        self.locator = locator
        self.cls = cls
        self.invert = invert

    def __call__(self, driver):
        el = driver.find_element(*self.locator)
        classes = el.get_attribute("class").split()
        if (self.cls in classes) != self.invert:
            return el
        return False
