google-music-automation
=======================

This is a collection of useful scripts for automating the management of your music in Google Music. These scripts rely on the Unofficial Google Music API locaed here: <https://github.com/simon-weber/gmusicapi>

Usage
-----

* Export environment variables for your Google username and password
(the password should be a app-specific generated using google settings)

`export USERNAME=bob`

`export PASSWORD=password123`


* Create your python script, import the module, and then create a instance
of the class. For example, to dump your library to json:

`from googlemusic_util import GoogleMusic_Util`

`util = GoogleMusic_Util()`

`util.DumpLibrary('library.json')`


Note
-----
When you log in with this utility, it registers your computer as an authorized device. You can only deregister 4 devices per year according to Google's policy.