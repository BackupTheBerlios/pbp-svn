import ClientForm as _CF
import ClientCookie as _CC
import mechanize as _mz
import urllib2 as _u2

class PBPScriptError(Exception):
    """Type for all pbpscript errors for easier catching"""

# group together the ones that could be caused by errors
# in your web application (as distinct from errors in pbp's code 
# itself)
webinteraction_errors = (PBPScriptError,
                         _u2.HTTPError, 
                         _u2.URLError,
                         _CF.ControlNotFoundError, 
                         _CF.ParseError,
                         _CF.ItemNotFoundError, 
                         _CF.ItemCountError,
                         _CC.LoadError, 
                         _CC.RobotExclusionError,
                         _mz.BrowserStateError, 
                         _mz.FormNotFoundError,
                         _mz.LinkNotFoundError,
                         )

class FailedPyloadError(PBPScriptError):
    def __init__(self, filename):
        self.filename = filename
    def __str__(self):
        t = "%s was not found or did not contain a variable named __pbp__"
        return t % (self.filename,)

class NoResponseError(PBPScriptError):
    """An attempt to access the last_res failed because no response
    has been seen from the server
    """
    def __str__(self):
        t = "failed because there was no response from the server"
        return t
    __repr__ = __str__


class TimedOutError(PBPScriptError):
    """Too much time elapsed (do_endtimer)"""
    def __init__(self, expected, elapsed):
        self.expected = expected
        self.elapsed = elapsed
    def __str__(self):
        t = "Operation took %s seconds but %s was the maximum"
        return t % (self.elapsed, self.expected)

class MissingFormError(PBPScriptError):
    def __init__(self, formspec):
        self.formspec = formspec
    def __str__(self):
        return "No form %s found on the page." % (self.formspec,)
    __repr__ = __str__

class NoCodeMatchError(PBPScriptError):
    def __init__(self, expected, response, code):
        self.expected = expected
        self.response = response
        self.code = code
    def __str__(self):
        if self.response:
            t = "\
Page %(url)s came back with code %(code)s but you expected %(expected)s"
            return t % dict(url=self.response.wrapped.url, code=self.code,
                            expected=self.expected) 
        else:
            t = "Server error code was %(code)s but you expected %(expected)s"
            return t % dict(code=self.code,
                            expected=self.expected)
    __repr__ = __str__

class DataNotFoundError(PBPScriptError):
    """text expected by the find command (or the stopat
    argument of go/submit/follow) was not found
    """
    def __init__(self, expected, response):
        self.response = response
        self.expected = expected # the string used to search
    def __str__(self):
        t = "Page %s didn't match the search string: %s"
        return t % (self.response.wrapped.url, self.expected)
    __repr__ = __str__

class DataFoundInappropriatelyError(PBPScriptError):
    """text expected by the nofind command (or the stopat
    argument of go/submit/follow) was found and shouldn't have been
    """
    def __init__(self, expected, response):
        self.response = response 
        self.expected = expected # the string used to search
    def __str__(self):
        t = "Page %s matched the search string, even though it shouldn't have: %s"
        return t % (self.response.wrapped.url, self.expected)
    __repr__ = __str__

class PBPUsageError(PBPScriptError):
    def __init__(self, command):
        self.command = command
    def __str__(self):
        fullcmd = self.command
        shortcmd = fullcmd.split(' ', 1)[0]
        return "This command failed: %s (try help %s)" % (fullcmd, shortcmd)

    __repr__ = __str__

class FieldValueError(PBPScriptError):
    def __init__(self, val):
        self.val = val
    def __str__(self):
        return "The value %s specified for the field was impossible.  (Did you forget a + or -?)" % (self.val,)
    __repr__ = __str__


