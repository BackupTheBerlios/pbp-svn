import re

version_info = ('0', '2', '2', None)
svn_head_url = "$HeadURL$"
if re.search("/pbp/tags/", svn_head_url):
    version = ".".join(version_info[:3])
else:
    version = ".".join(version_info[:3]) + '+'
