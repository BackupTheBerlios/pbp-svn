version_info = ('0', '3', '0', None)
svn_head_url = "$HeadURL$"
if svn_head_url.find("/pbp/tags/") >= 0:
    version = ".".join(version_info[:3])
else:
    version = ".".join(version_info[:3]) + '+'
