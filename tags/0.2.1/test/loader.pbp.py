def test(*args):
    return "ttteeeeeesssssssssttt %s" % (' '.join(args),)

uri = 'http://pbp.berlios.de'
link = 'Wiki'

dont_export = '1'

__pbp__ = ['uri', 'link', 'test']
