"""Basics of the language:
HTTP Requests
=============
    go <uri> [stopat] - navigate to a url
    submit <form>[%submitspec] [stopat] - submit the named form 
    follow <linkspec>[%NNN] [stopat] - look in the html for a link, then
                                       jump through it
Examining Responses
===================
    code <NNN> [<NNN> [<NNN> ...]] - check that the code of the last response
                                     is NNN.  You can also use 30* or 3*
                                     for example, to match 301, 302, 303...
    find <regex> - check that regex is in the response data
    notfind <regex> - check that regex is not in the response data

Local Browser Access
====================
    formvalue <form> <field>[%NNN] <value> - set value for field on form
    back      - go back in the browser history, if possible
    show      - dump the data in the last response (e.g. the HTML page)
    showform  - print a concise summary of forms on the page

Misc
====
    history [filename] - show the history of your commands, or write
                         it to a file.
    timeout <time> - give up on a browser session after <time> seconds
    starttimer - start a timed interval
    endtimer [max] - end the timer, and show how much time elapsed
    pyload <filename>  - exec <filename>, look for an object named pbpnames
                         in resulting namespace, and add it to the dict of
                         callables
    do <python_callable> [arguments] - call some python code defined
                                       in a previously-pyload'd file
    done/quit/exit - hang up the phone

Note on [stopat] argument:
    This is always the last argument of a "HTTP Request"-type command.  
It is a regular expression.  HTTP requesting works like this:
    1. follow redirects and refreshes with time 0, stopping on page A.
    2. if stopat is not provided, stop.
    3. if stopat is provided:
       i) if the stopat string is found on page A, stop.
       ii) if there is a refresh, wait for it to time out, follow it to page B
           and start over 
       iii) otherwise, it's an error; stop and complain as if find <stopat>
            had been done.
Continue following the steps until we hit the defined timeout or a stop.
"""
from twisted.python import threadable, log, failure, usage, util
threadable.init(1)
from twisted.internet import reactor, defer, threads

import sys
import time, Queue
import mimetypes
import threading

import cmd, shlex, re
import fnmatch

import urllib2, mechanize, ClientCookie, ClientForm

# sibling
from pbp import error

shlex_split = lambda s: shlex.split(s, comments=True)
tprintln = lambda *s: reactor.callFromThread(util.println, *s)

def trunc(s, length, end=1):
    """Truncate a string s to length length, by cutting off the last 
    (length-4) characters and replacing them with ' ...'
    With end=0, truncate from the front instead.
    """
    if len(s) > length:
        if end:
            return s[:-4] + '...'
        return '...' + s[4:]
    return s


class NewTimeout(Exception):
    """Report that a new timeout is needed"""
    def __init__(self, time):
        self.time = time
    def __str__(self):
        return "New timeout of %s seconds requested" % (self.time,)

class PBPShell(cmd.Cmd, object):
    prompt = 'PBP> '
    def tprintln(self, *args):
        self.stdout.write(' '.join([str(a) for a in args]) + '\n')

    def __init__(self, canfail=0):
        self.browser = mechanize.Browser()
        # handle refresh and meta refresh with time 0
        self.browser.set_handle_equiv(ClientCookie.HTTPEquivProcessor)
        self.browser.set_handle_refresh(ClientCookie.HTTPRefreshProcessor)
        # TODO - utidylib handler
        self.last_res = None
        self.refresh_target = None
        self.refresh_time = -1
        self.timeout = 300
        self.stored_time = -1
        self.canfail = canfail  # canfail=1 to make exceptions end loop 
        self.history = []
        self.filename = "<interactive>"
        cmd.Cmd.__init__(self)

    def journey(self, browsemethod):
        """
        Go there, and set up refreshes for later.
        stopat is a regular expression to look for.  See help(pbpscript)
        TODO - check for any javascript that might be trying to send
        us away, too.
        """
        try:
            self.last_res = browsemethod()
            self.last_code = self.last_res.wrapped.code
        except urllib2.HTTPError, e:
            self.tprintln(e)
            self.last_res = None
            self.last_code = e.code
            return
        refresh = self.last_res.wrapped.info().getheader('REFRESH')
        if refresh:
            self.refresh_time, self.refresh_url = self._parseRefresh(refresh)

    def journeyAndRefresh(self, browsemethod, stopat=None):
        while 1:
            self.journey(browsemethod)

            if not self.last_res:
                return
            if stopat is None:
                self.tprintln('done at %s' % (self.last_res.wrapped.url))
                return
            else:
                try:
                    last_data = self._extractResponseData()
                except error.NoResponseError:
                    return
                if re.search(stopat, last_data, re.I): 
                    self.tprintln('found expr in page %s'%(self.last_res.wrapped.url,))
                    return
                if self.refresh_time > 0:
                    time.sleep(self.refresh_time)
                    self.refresh_time = -1
                    browsemethod = (lambda :
                        self.browser.open(self.refresh_url))
                else:
                    raise error.DataNotFoundError(stopat, self.last_res)


    def _parseRefresh(self, st):
        """Return time and url for a refresh header"""
        refresh_time_s, urlblob = [s.strip() for s in st.split(';')]
        reftime = int(refresh_time_s)
        m = re.match('url\s*=(.*)', urlblob, re.I)
        if m and m.group(1):
            url = m.group(1)
        else:
            url = urlblob
        return reftime, url

    def do_history(self, rest):
        """history [filename]
        Show your command history for this session, or save it to a file.
        """
        args = shlex_split(rest)
        history = '\n'.join(self.history)
        if args:
            fn = args[0]
            file(fn, 'w').write(history)
        else:
            self.tprintln("### Begin history ###")
            self.tprintln(history)
            self.tprintln("### End history ###")

    def do_timeout(self, rest):
        """timeout <time>
        Time is in seconds.  After <time> seconds have elapsed,
        give up on the script and exit the session.  (Does nothing in
        the interactive interpreter.)

        Useful for kicking a script out of an infinite loop that may be 
        caused by a bug in your application.  Should be the first thing 
        in your script; default is 300 (5 minutes).  Contrast to endtimer.
        """
        args = self._getCountedArgs("timeout " + rest, 1)
        newtime = int(args[0])
        self.tprintln('new timeout %s' % (newtime,))
        raise NewTimeout(newtime)

    def do_code(self, rest):
        """code [<NNN> [<NNN> ...]]
        <NNN> can be a number like 404, or it can be a pattern like 40* or 4*
        """
        actual = str(self.last_code)
        codes = shlex_split(rest)
        if not codes:
            self.tprintln(self.last_code)
            return
        for expected in codes:
            if fnmatch.fnmatch(actual, expected):
                self.tprintln('OK: code was %s' % (actual,))
                return
        raise error.NoCodeMatchError(expected, self.last_res, self.last_code)
    
    def do_find(self, rest):
        """find <regex>
        Look for <regex> in the response data, give an error if the string
        isn't found.
        """
        args = self._getCountedArgs("find " + rest, 1)
        data = self._extractResponseData()
        searchst = args[0]
        if re.search(searchst, data, re.I):
            self.tprintln('OK: found %s' % (searchst,))
            return
        raise error.DataNotFoundError(searchst, self.last_res)

    def do_notfind(self, rest):
        """notfind <regex>
        look for <regex> in the response data, give an error if the string
        *is* found.  
        (Inverse of the find command)
        """
        args = self._getCountedArgs("notfind " + rest, 1)
        data = self._extractResponseData()
        searchst = args[0]
        if not re.search(searchst, data, re.I):
            self.tprintln('OK: page didn\'t contain %s' % (searchst,))
            return
        raise error.DataFoundInappropriatelyError(searchst, self.last_res)

    def do_back(self, rest):
        """Go back in browser history"""
        res = self.browser.back()
        self.last_res = res
        self.last_code = res.wrapped.code
        self.tprintln("OK, back at %s" % (res.wrapped.url,))
    
    def do_starttimer(self, rest):
        """Start timer - use endtimer later to get the time elapsed"""
        self.stored_time = time.time()
        self.tprintln("Started the timer.")
    
    def do_endtimer(self, rest):
        """endtimer [max]
        End timer - use after starttimer to see time elapsed.  If max
        is given, raise an error if more than max seconds have passed.

        Useful for performance/load tests where you know an action
        will succeed and you want to make sure it succeeds in a reasonable
        amount of time.  Because endtimer is an explicit action, it 
        can't be used to break an infinite loop; use timeout for that.
        """
        args = shlex_split(rest)
        expected = sys.maxint
        if args:
            expected = int(args[0])
        elapsed = time.time() - self.stored_time
        if elapsed > expected:
            raise error.TimedOutError(expected, elapsed)
        self.tprintln("%0.2f seconds elapsed" % (elapsed,))

        self.stored_time = -1
    
    def do_go(self, rest):
        """go <uri> [stopat]
        navigate to <uri>.  If stopat is given (a regular expression),
        try to keep going until a page is found with that text.
        If the link never reaches a page containing stopat, give
        an error like find (help find for details).
        """
        args = self._getCountedArgs("go " + rest, 1, 2)
        stopat = None
        if len(args) > 1:
            stopat = args[1]

        self.journeyAndRefresh(lambda : self.browser.open(args[0]), stopat)

    def do_pdb(self, rest):
        """debugger"""
        import pdb; pdb.set_trace()

    def do_showform(self, rest):
        """Summarize the forms on the page"""
        for n,f in enumerate(self.browser.forms()):
            if f.name:
                self.tprintln("Form name=%s" % (f.name))
            else:
                self.tprintln("Form # %s" % (n+1))
            if f.controls:
                self.tprintln("## __Name______ __Type___ __ID________ __Value__________________")
            clickies = [c for c in f.controls if c.is_of_kind('clickable')]
            nonclickies = [c for c in f.controls if c not in clickies]
            for field in nonclickies:
                if hasattr(field, 'possible_items'):
                    value_displayed = "%s of %s" % (field.value,
                                                    field.possible_items())
                else:
                    value_displayed = "%s" % (field.value,)
                strings = ("  ",
                           "%-12s %-9s" % (trunc(str(field.name), 12),
                                           trunc(field.type, 9)),
                           "%-12s" % (trunc(field.id or "(None)", 12),),
                           value_displayed,
                           )
                self.tprintln(*strings)
            for n, field in enumerate(clickies):
                strings = ("%-2s" % (n+1,),
                           "%-12s %-9s" % (trunc(field.name, 12),
                                           trunc(field.type, 9)),
                           "%-12s" % (trunc(field.id or "(None)", 12),),
                           field.value,
                           )
                self.tprintln(*strings)
            
    def do_show(self, rest):
        """Show the data in the last http response.
        """
        self.tprintln(self._extractResponseData())

    def do_done(self, rest):
        """Quit"""
        self.tprintln('Bye.')
        sys.exit(0)
    do_EOF = do_exit = do_quit = do_done

    def _pickForm(self, formspec):
        """Set the current form to one found with formspec"""
        self.browser.form = None
        if formspec.isdigit():
            try:
                self.browser.select_form(nr=(int(formspec)-1))
            except mechanize.FormNotFoundError, e:
                pass
        try:
            self.browser.select_form(formspec)
        except mechanize.FormNotFoundError, e:
            pass
        if self.browser.form is None:
            raise error.MissingFormError(formspec)

    def _smartFieldKey(self, field, transform=None):
        """Look for a control in the order: name, id, type, nr.
        When found, return the necessary kwarg dict to find the control again.
        Parse %NNN if necessary.

        e.g.

        fldfinder = self._smartFieldKey('textarea%2') 
        # ...fldfinder is {'type':str('textarea'), 'nr':1}
        self.browser.set_value('unf', **fldfinder)

        Transform is a dict which will map a field value
        into the expected type for that field.  Default is
        {'name': str, 'id': str, 'type': str}

        Don't blame me, I just work here.
        """
        if transform is None:
            transform = dict(name=str, id=str, type=str)
        fieldparts = _unPercent(field)
        field = fieldparts.pop(0)
        nth = -1
        if fieldparts:
            nth = int(fieldparts[0]) - 1
        last_err = None
        for ident in transform:
            kwargs = {ident:transform[ident](field)}
            if nth>=0:
                kwargs['nr'] = nth
            try:
                if self.browser.find_control(**kwargs):
                    return kwargs
            except ClientForm.ControlNotFoundError, e:
                last_err = e
                continue
        raise last_err

    def _getCountedArgs(self, command, count, optional_count=None):
        """Raise a PBPUsageError unless the number of args is either 
        count or optional_count.  Return a list of args.
        """
        if optional_count is None: optional_count == count

        args = shlex_split(command)[1:]
        if len(args) not in (count, optional_count):
            raise error.PBPUsageError(command)
        return args

    def do_formvalue(self, rest):
        """formvalue <form> <field>[%NNN] <value>
        Set field to value on form form.  For un-named forms,
        form can also be an integer for the Nth form.  The showform
        command will provide the information you need.

        If a number is given after field, choose the NNN'th field named
        field instead of the first.  (Most often used for forms with password
        verification fields.) To choose a field with a literal % in the name,
        type \%.

        Examples:
            formvalue newuser username bob
            formvalue newuser password thebuilder
            formvalue newuser password%2 thebuilder 

        MULTIPLE SELECTIONS:
        For fields with multiple selections, such as <input type="radio">
        and <select>, you must specify the value with a + or - indicating
        on or off.  With <select multiple> you can turn on more than one
        value with successive formvalue commands.

        Examples:
            formvalue choosecourse course +algebra
            formvalue choosecourse preferred_teachers +"Mrs. Brunswick"
            formvalue choosecourse preferred_teachers +"Mr. Wiggedywack"
        """
        args = self._getCountedArgs("follow " + rest, 3)
        formname = args.pop(0)
        fieldspec = args.pop(0)
        value = ' '.join(args)

        self._pickForm(formname)

        fieldfinder = self._smartFieldKey(fieldspec)

        ctl = self.browser.find_control(**fieldfinder)
        if ctl.type in ['text', 'password', 'textarea']:
            self.browser.set_value(value, **fieldfinder)
        elif ctl.type == 'checkbox':
            state = _parseBool(value)[0]
            self.browser.set_single(state, **fieldfinder)
        elif ctl.type in ['radio', 'select']:
            state, selection = _parseBool(value)
            self.browser.set(state, selection, **fieldfinder)
        elif ctl.type in ['submit', 'image', 'hidden', 'reset']:
            return
        elif ctl.type == 'file':
            self.browser.add_file(open(value, 'r'), 
                                  value, 
                                  mimetypes.guess_type(value)[0])
        fieldname = ''
        for k in fieldfinder:
            if k != 'nr':
                fieldname = fieldfinder[k]
                break
        self.tprintln("Set %s in %s to value %s" % (fieldname, formname, value))

    do_fv = do_formvalue


    def do_submit(self, rest):
        """submit <form>[%submitspec] [stopat]
        Use the name=value pairs to set the form fields, then
        submit the form.  Otherwise behave like go (see help go for
        details).
        If submit is given, use it as an exact string to identify 
        the submit button (by name, type, or id in that order).

        To choose a form with a literal % in the name, type \%.
        """
        args = self._getCountedArgs("submit " + rest, 1, 2)
        formparts = _unPercent(args[0])
        formname = formparts.pop(0)
        submit = None
        if formparts:
            submit = formparts[0]
        stopat = None
        if args[1]:
            stopat = args[1]


        self._pickForm(formname)

        last_res_old = self.last_res
        last_err = None
        ident_map = dict(name=str, type=str, id=str, nr=lambda n: int(n)-1)
        if submit:
            for ident in ('name', 'type', 'id', 'nr'):
                kwargs = {ident: ident_map[ident](submit)}
                requester = lambda: self.browser.submit(**kwargs)
                try:
                    self.journey(requester)
                except ClientForm.ControlNotFoundError, e:
                    last_err = e
            # if the response still hasn't changed, we didn't get anywhere
            if self.last_res is last_res_old:
                raise last_err

        else:
            self.journey(lambda : self.browser.submit())
         
        self.journeyAndRefresh(lambda: self.last_res, stopat)

    def do_follow(self, rest):
        """follow <linkspec>[%NNN] [stopat]

        Attempt each method for finding a link, in this order:
        url_regex, text_regex, name_regex, tag.  Otherwise behave like go
        (see help go for details).

        linkspec is one of url, text, name, tag.  If a number is
        given after matchable_string, choose the NNN'th link matching that,
        not the first one.  
        
        To use a literal % in matchable_string, type \%.

        Examples: 
            follow /courses/healthed    # a url
            follow Courses              # the visible text in the link
            follow "click here"%3       # the 3rd link with text "click here"
            follow Logout loginform     # click the link with text "Logout" &
                                        # keep following redirects until
                                        # a page with "loginform" is found.
        """
        args = self._getCountedArgs("follow " + rest, 1, 2)
        matchparts = _unPercent(args.pop(0))
        matchable = matchparts.pop(0)
        nth = 0
        if matchparts:
            nth = matchparts[0]

        stopat = None
        if args:
            stopat = args[0]

        # three of them take regular expressions and one takes
        # a string, so decide how to decode the given argument
        # based on what kind of thing we're looking for
        matchingmap = dict(url_regex = re.compile,
                           text_regex = re.compile,
                           name_regex = re.compile,
                           tag = str)
        thelink = None
        # try each of url, text, name, tag for the string given to locate
        for matcher in matchingmap:
            try:
                matchconverter = matchingmap[matcher]
                kwargs = {matcher:matchconverter(matchable), 'nr': nth}
                thelink = self.browser.find_link(**kwargs)
                break
            except mechanize.LinkNotFoundError, e:
                # keep going in case one of the other methods
                # gets a hit, but remember the last thing
                # we tried so we can re-raise later if not.
                last_err = e
                continue
        if not thelink:
            self.tprintln("oops!  couldn't find any link like %s" % (matchable,))
            raise last_err

        self.journeyAndRefresh(lambda : self.browser.follow_link(**kwargs), 
                               stopat)

    def abort(self, reason):
        """Abort the current script, with the reason given"""
        self.deferred.errback(reason)


    def do_pyload(self, rest):
        """pyload <filename>
        Load <filename> by searching first in the same directory as
        the running script, then by searching in the current working
        directory.  The file should contain a variable named __pbp__
        which is a list of the names to make available to the pbp
        interpreter.
        """
        args = self._getCountedArgs("pyload " + rest, 1)
        fn = args[0]
        globalns = globals()
        globalns['PBP'] = self
        self.tprintln("Loading file %s" % (fn,))
        for _f in (util.sibpath(self.filename, fn), fn):
            try:
                execfile(_f, globalns)
                break
            except EnvironmentError, e:
                pass
        try:
            self._loaded_names = {}
            for name in globalns:
                if name in globalns['__pbp__']:
                    self._loaded_names[name] = globalns[name]
        except KeyError:
            raise error.FailedPyloadError(fn)


    def do_do(self, rest):
        """do <python_callable> [arguments...]"""
        args = shlex_split(rest)
        try:
            name = args.pop(0)
        except IndexError:
            raise PBPUsageError("do " + rest)
        ret = self._resolvePyloadedName(name, *args)
        if ret is not None:
            self.tprintln(str(ret))

    def _resolvePyloadedName(self, name, *args):
        """Return the str of either the obj or the result of calling
        the obj.
        """
        obj = self._loaded_names[name]
        if callable(obj):
            ret = obj(*args)
        else:
            ret = obj
        return ret


    def _extractResponseData(self):
        if not self.last_res:
            raise error.NoResponseError()
        self.last_res.seek(0)
        return self.last_res.read()

    def emptyline(self):
        pass

    def default(self, line):
        if line.strip().startswith('#'):
            pass
        else:
            cmd.Cmd.default(self, line)

    def onecmd(self, line):
        try:
            self.history.append(line)
            # resolve $ strings in line
            args = shlex_split(line)
            for n, a in enumerate(args[:]):
                if a.startswith('$'):
                    try:
                        args[n] = self._resolvePyloadedName(a[1:])
                    except KeyError:
                        pass # args[n] will be a string beginning with $
            line = ' '.join([s.replace(' ', r'\ ') for s in args])
            return cmd.Cmd.onecmd(self, line)
        except (SystemExit, NewTimeout), e:
            raise
        except error.PBPScriptError, e:
            self.tprintln("*** ERROR ***")
            self.tprintln(e)
            if self.canfail:
                raise
        except Exception, e:
            self.tprintln("*** ERROR ***")
            log.err()
            if self.canfail:
                raise

        return 0
        
    def postloop(self):
        reactor.stop()



def _parseBool(s):
    """Determine if s is a string indicating that user intends
    to set a control to the on state, e.g. 'y' or '+foo'
    Return 2-tuple of (on-state, value)
    """
    if s.startswith('-'): return False, s[1:]
    if s.startswith('+'): return True, s[1:]
    if s.lower() in ['y', 'yes', 'on', 'true', '1']:
        return True, None
    if s.lower() in ['n', 'no', 'off', 'false', '0']:
        return False, None
    raise error.FieldValueError(s)

def _unPercent(st):
    """Return 2-tuple of (leftpart, rightpart)
    where rightpart is the part after any unadorned %
    and leftpart is the unquoted part before the %.
    """
    ust = unicode(st)
    ust.replace(r'\\', u'\ufffd')
    ust.replace(r'\%', '%')
    ust.replace(u'\ufffd', '\\')
    return [str(x) for x in ust.split('%', 1)]


 
#
class BatchThread(threading.Thread):
    """Run commands from all scripts, non-interactively"""
    def __init__(self, deferred, scripts, cascade=0):
        self.cascade = cascade # if 1, any errors stop all scripts at once
        self.scripts = scripts
        self.deferred = deferred
        self._more_scripts = 1 # set to 0 to prevent running any scripts 
                               # that still haven't been processed
        self.message_queue = Queue.Queue()
        self.waiting = 1
        threading.Thread.__init__(self)
        self.succeeded = 0

    def cb_scriptDied(self, failed, script):
        tprintln(failed)
        tprintln('*** FAILURE: %s ***' % (script,))
        if self.cascade:
            self._more_scripts = 0
        self.waiting = 0

    def cb_scriptPassed(self, _dontcare, script):
        tprintln('SUCCESS: %s' % (script,))
        self.succeeded = 1

    def cb_trapStopRequested(self, failed, script):
        """A script thread that had already timed out kept going,
        and raised StopRequested.  Just ignore.
        """
        failed.trap(StopRequested)

    def run(self):
        try:
            shell = PBPShell(canfail=1)
            
            for s in self.scripts:
                if self._more_scripts:
                    d = defer.Deferred()
                    t = ScriptThread(d, s, shell, self.message_queue)
                    d.addCallback(lambda r: self.cb_scriptPassed(r, s))
                    d.addErrback(lambda f: self.cb_trapStopRequested(f, s))
                    d.addErrback(lambda f: self.cb_scriptDied(f, s))
                    self.succeeded = 0
                    self.waiting = 300
                    def later():
                        t.timer = reactor.callLater(self.waiting, 
                                                    self._doneWaiting,
                                                    t,
                                                    s)
                    reactor.callFromThread(later)
                    t.start()
                    self._waitScript(t, s)
                else:
                    tprintln('*** Cascaded FAILURE: %s ***' % (s,))
            reactor.callFromThread(self.deferred.callback, None)
        except Exception, e:
            reactor.callFromThread(self.deferred.errback, e)

    def _waitScript(self, a_thread, script):
        while self.waiting and not self.succeeded:
            try:
                timeout = self.message_queue.get_nowait()
                if a_thread.timer:
                    a_thread.timer.cancel()
                self.waiting = timeout.time
                def later():
                    a_thread.timer = reactor.callLater(timeout.time, 
                                                       self._doneWaiting,
                                                       a_thread,
                                                       script)
                reactor.callFromThread(later)
            except Queue.Empty:
                pass
            time.sleep(0.1)

    def _doneWaiting(self, a_thread, script):
        """After a timeout, all scripts fail.  Turn on cascade, tell
        the thread we don't care if it keeps going, and call 
        the failure callback.
        """
        a_thread.keepgoing = 0
        self.cascade = 1
        self.cb_scriptDied(error.TimedOutError(self.waiting, self.waiting),
                           script)


class ScriptThread(threading.Thread):
    """Run commands of a single script"""
    def __init__(self, deferred, script, shell, message_queue):
        self.deferred = deferred
        self.script = script
        self.shell = shell
        self.shell.filename = self.script
        self.message_queue = message_queue
        self.keepgoing = 1 # set to 0 from parent thread to stop
        threading.Thread.__init__(self)
        self.setDaemon(1) # if reactor stops, I will stop
        self.timer = None

    def run(self):
        try:
            for command in file(self.script, 'r'):
                if self.keepgoing:
                    try:
                        self.shell.onecmd(command)
                    except NewTimeout, t:
                        self.message_queue.put(t)
                else:
                    raise StopRequested()
            reactor.callFromThread(self.deferred.callback,None)
        except Exception, e:
            reactor.callFromThread(self.deferred.errback,e)

class StopRequested(Exception):
    """The thread was asked not to keep going by parent"""


#
def interactiveLoop():
    shell = PBPShell()
    shell.cmdloop()



class PBPOptions(usage.Options):
    optFlags = [
                ['cascade-failures', 'C', '''\
If any one script fails, the remaining scripts will not run and will report
failure.'''],
                ]
    def parseArgs(self, *scripts):
        self['scripts'] = scripts 

def bye(result):
    log.msg(result)
    reactor.stop()

def gotExit(failure):
    failure.trap(SystemExit)
    reactor.stop()


def run(argv=sys.argv):
    o = PBPOptions()
    o.parseOptions(argv[1:])
    if o['scripts']:
        d = defer.Deferred()
        batch = BatchThread(d, o['scripts'], o['cascade-failures'])
        reactor.callLater(0, batch.start)
        gotError = lambda f: (log.err(), reactor.stop())
    else:
        d = threads.deferToThread(interactiveLoop)
        gotError = lambda f: log.err()
    d.addCallback(bye)
    d.addErrback(gotExit).addErrback(gotError)
    reactor.run()

