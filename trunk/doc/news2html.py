import warnings
warnings.filterwarnings('ignore')

import sys, os
import gettext

from nevow import rend, loaders, appserver, tags as T
from twisted.internet import reactor
from twisted.python import usage, util

import yaml

import sre
def got_char(scanner, token): return token
def got_link(scanner, token):
    # strip start and end brackets
    token = token[1:-1]
    
    words = token.split()
    url = words[-1]
    rest = ' '.join(words[:-1])

    return T.a(href=url)[rest]
def got_bracket(scanner, token): return '['

def got_uglyDquo(scanner, token):
    return (u"\u201c%s\u201d" % (token[1:-1],)).encode('utf8')

def got_uglySquo(scanner, token):
    return (u"\u2018%s\u2019" % (token[1:-1],)).encode('utf8')

tokens = [(r'\[\[', got_bracket),
          (r'"[^"]*"', got_uglyDquo),
          (r"'[^']*'", got_uglySquo),
          (r'\[[^\]]+\]', got_link),
          ('.', got_char),
          ]
scanner = sre.Scanner(tokens)

class Page(rend.Page):
    def __init__(self, data, countItems, *args, **kwargs):
        rend.Page.__init__(self, *args, **kwargs)
        self.data = data
        self.countItems = countItems # number of news items to grab
    def render_news(self, ctx, data):
        markup = []
        append = markup.append
        for i in self.data['news'][:self.countItems]:
            append(T.p(_class='datetime')[i['date']])
            append(T.h3[i['title']])
            for para in i['c'].split('\n'):
                if para.strip() == '': continue
                append(self._render_para(para))
                append('\n')
        return markup
    def render_download(self, ctx, data):
        ctx.fillSlots('latest', str(self.data['release']))
        return ctx.tag
    def _render_para(self, para):
        text = []
        nodes = []
        para = ' '.join(para.splitlines())
        scanned = scanner.scan(para)
        for tok in scanned:
            nodes.append(tok)
        return T.p[nodes]

class Options(usage.Options):
    synopsis = 'news2html [options] <yaml-data> [<xhtml-template>]'
    optParameters = [['count', 'c', '3', 'How many news items to include'],
                     ['output', 'o', 'html',
                      'Output format, either "html" or "rss"'], 
                     ]
    def parseArgs(self, yaml, xhtml=None):
        if xhtml is None:
            xml = util.sibpath(__file__, 'pbp.xhtml')
        else:
            xml = xhtml
        self['template'] = xml
        self['yaml'] = yaml
        self['count'] = int(self['count'])


def run(argv=None):
    if argv is None:
        argv = sys.argv
    o = Options()
    try:
        o.parseOptions(argv[1:])
    except usage.UsageError, e:
        sys.stderr.write(str(o))
        sys.stderr.write('%s\n' % (str(e),))
        return 1

    print getHtml(o['yaml'], o['count'], o['template'])
    return 0

def getHtml(yamlfile, countItems, template):
    ydata = list(yaml.loadFile(yamlfile))[0]
    Page.docFactory = loaders.xmlfile(template)

    d = Page(ydata, countItems).renderString()

    output = []
    d.addCallback(cb, output)
    d.addErrback(eb)
    reactor.run()

    return output[0]

def cb(r, out):
    out.append(r)
    reactor.callLater(0, reactor.stop)

def eb(f):
    try:
        raise f.value
    finally:
        reactor.callLater(0, reactor.stop)

if __name__ == '__main__':
    sys.exit(run())
