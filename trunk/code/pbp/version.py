import re

version_info = ('0', '2', '1', None)
svn_head_url = "$HeadURL$"
if re.match("/pbp/tags/", svn_head_url):
    version = ".".join(version_info[:3])
else:
    version = ".".join(version_info[:3]) + '+'
