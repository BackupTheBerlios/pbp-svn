
                          Python Browsing Probe (PBP)

About

   PBP is a web test tool based on John J. Lee's mechanize. It exposes the
   browser functionality at the level of a shell-like interpreter so that
   testers can quickly write tests in a simple language designed specifically
   for that purpose. Anyone familiar with a command line should be able to
   write test scripts for even the most complex web applications with PBP.

   More detail is available at the Wiki.

   PBP is MIT-licensed.  Refer to LICENSE.txt for the text of this license.

Prerequisites (Dependencies)

     * Download Twisted
http://twistedmatrix.com/products/download
     * Download ClientCookie
http://wwwsearch.sf.net/ClientCookie/#download
     * Download ClientForm
http://wwwsearch.sf.net/ClientForm/#download
     * Download pullparser
http://wwwsearch.sf.net/pullparser/#download
     * Download mechanize
http://wwwsearch.sf.net/mechanize/#download

Installing:

   Make sure you have the above prerequisites installed.  Then:

   $ python setup.py install

   On Windows, you can also get a self-installing executable at the download
   site listed at the bottom.  Please note that the Windows package 
   contains code created by third parties, and their licenses are
   installed with the rest of the software.  You must obey these
   third party licenses as well as LICENSE.txt if you wish
   to redistribute pbp as a Windows package.

How-To

 $ python pbpscript
 PBP> go http://mailinator.com
 done at http://www.mailinator.com/mailinator/Welcome.do
 PBP> code 200
 OK: code was 200
 PBP> find "property of Outsc.*me"
 OK: found property of Outsc.*me
 PBP> showform
 Form name=search
 ## __Name______ __Type___ __ID________ __Value__________________
    email        text      (None)      
 PBP> formvalue search email pbp.berlios.de
 Set email in search to value pbp.berlios.de
 PBP> submit search
 done at http://www.mailinator.com/mailinator/CheckMail.do
 PBP> code 200
 OK: code was 200
 PBP> find "no mensajes"
 *** ERROR ***
 Page http://www.mailinator.com/mailinator/CheckMail.do didn't match the search
 string: no mensajes
 PBP> find "NO MESSAGES"
 OK: found NO MESSAGES
 PBP> back
 OK, back at http://www.mailinator.com/mailinator/Welcome.do
 PBP> history
 go http://mailinator.com
 code 200
 find "property of Outsc.*me"
 showform
 formvalue search email pbp.berlios.de
 submit search
 code 200
 find "no mensajes"
 find "NO MESSAGES"
 back
 history
 PBP> history mylog.txt
 PBP> quit
 Bye.

Downloads

   http://pbp.berlios.de

Source Code / SVN

   To check out the source code for PBP:

   $ svn co svn://svn.berlios.de/pbp/trunk pbp

   You can use A-A-P to build packages from the included main.aap file.
