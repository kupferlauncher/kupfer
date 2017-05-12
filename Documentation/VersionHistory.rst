NEWS for kupfer
===============

kupfer v319
-----------

+ Fix *Get Parent Folder* to always return a ``FileLeaf`` (not a subclass)

+ Plugins:

  + In *Rhythmbox*, always use song uris for enqueueing tracks (fixes an issue
    with legacy encoded file paths).
  + In *Rhythmbox*, improve error reporting on errors in *Get File*.
  + Add *Prefer Dark Theme* that allows you to flip this GTK setting just
    for Kupfer

kupfer v318
-----------

+ Refactor some of the UI so that it uses composition instead of inheritance
  for Gtk widgets. No functional changes intended (except given below).
+ The result list for the third pane now sticks to the right side.

+ Plugins:

  + In *Rhythmbox*, keep the cache even if the player is not running (#75).
  + In *Rhythmbox*, fix a bug where songs would sometimes be skipped in the
    *Songs* catalog.
  + In *Media Player Control*, add item *Pause All*

kupfer v317
-----------

+ When an input method's preedit is active, backspace, return, arrows and
  other keys are now reserved for the input method (ibus-mozc was tested).
+ All exceptions from content decorators from plugins are now caught and
  logged (#73)
+ Fix remembering “Make (Action) Default for (Object)” when the object is
  a text or a shell command.
+ Change so that ``kupfer`` only reads from stdin when called with no
  arguments and when not started from a desktop file. This should fix issues
  with starting from autostart or menus in some environments. (#72)
+ Fix a crash when the *Show Text* window is closed. (#71)
+ (API) Trying to install a plugin setting key with a reserved name now raises
  an exception.

+ Plugins:

  + In *Recent Documents*, fix an exception with filenames in unknown encoding
  + In *Tracker*, fix an exception with malformed ``.savedSearch`` files.

kupfer v316
-----------

+ Bundle an icon used for windows and workspaces. Based on an icon in Adwaita.
+ Add two more default terminal alternatives, exo-open and x-terminal-emulator.
+ Add a few more alternatives in the drop down for large icon size

+ Plugins

  + In *Rhythmbox*, look for more album art filenames in the same directory
  + In *Firefox Keywords*, allow copying them to clipboard (Ctrl + C)
  + In *Text Files*, fix *Write To* and *Append To*
  + In *Tracker* support a location restriction for ``.savedSearch`` files.

kupfer v315
-----------

+ Fix an issue with launching X applications in wayland (#65)
+ Fix an exception on text input “file://”

+ Plugins

  + In *Volumes*, show a notification on successful unmounts (#64)
  + In *Documents* you can now opt out applications of having their recent
    documents listed inside.
  + In *Rhythmbox*, use less memory for storing the library cache
  + In *Rhythmbox*, sort albums of an artist primarily by year, then title.
  + In *Shell Commands*, fix the icon name of a command

kupfer v314
-----------

+ Replaced file action *Reveal* (file manager plugins do this better)
  with *Get Parent Folder* which has the default accelerator *P* and thus is
  very handy for navigation.
+ Fix so that right arrow can enter directories even in text mode
+ Allow **Action Accelerators** to use more than just A-Z keys
+ Misc fixes to start **wayland compatibility**. All uses of Wnck now
  gracefully disable when not applicable.
+ Wnck is now technically optional, still recommended for best experience in X.
+ Tweak arrangement of items in the first page of the preferences window,
  and add a few more icon size alternatives.
+ Tweak the multiple objects icon to look at bit better
+ Recognize pasted file:// uris as files

+ Plugins

  + New plugin for file manager *Nemo*
  + Fix *Rhythmbox* to not clear the queue when playing a single song
  + Fix *Rhythmbox* to handle missing files gracefully
  + Fix *Rhythmbox*, *Audacious* to not clear cached library/playlist when
    the respective program exits

kupfer v313
-----------

+ **Action Accelerators**: every action can have a configurable accelerator
  key that allows activating it directly.
+ Changed some default shortcuts:

  + *Select ‘Selected Text’* now uses Ctrl + G
  + *Switch to 1st Pane* now has no binding by default

+ Fix monitor placement in Unity (#45)
+ The preferences window now loads and shows current icon size
+ The configuration file is now written in sorted order.
+ Fix a minor visual issue using some themes (padding under match text)
+ The set keybinding window now has a button to clear the current binding
+ The result list now has a minimum size depending on the small icon size,
  so it sizes better for hidpi

+ Plugins

  + Handle errors better in *Tracker* and make *Get Tracker Results...*
    fetch the results asynchronously.
  + Fix *Dismiss* action in *Getting Things GNOME* plugin. Thanks
    @khurshid-alam for the patch!
  + Another *Create Task* action was added to GTG (an action on the app itself).
  + *Audacious* now refreshes when the program starts
  + *Attach in Email To* in *Thunderbird* is now not allowed on directories
  + *Notes* now has *(Note) → Append → (Text)* which is a reversal of
    an existing action
  + *Append To Note* now works for kzrnote as well

kupfer v312
-----------

*There are some lingering open bugs for desktop environments that are not my
main desktop. Kupfer only becomes what everyone puts in, so if you can help
fixing bugs related to your environment, please come to our github page.*

+ Add several new possible accelerator keys in the main kupfer interface:

  + *Select Pane 1, 2, 3*
  + *Select Clipboard Text*, *Select Clipboard File*
  + Configure them in the keyboard tab in preferences

+ ``Keybinder`` which is optional is now also treated as such by configure
+ (API) Minor bugfix so that async Tasks don't need to set a name
+ Plugins:

  + Handle errors better in the *Trash* plugin
  + Fix the way *Rhythmbox* starts playback of multiple songs
  + Add action *Get File* on *Rhythmbox* songs

kupfer v311
-----------

+ Work even if ``Keybinder`` is not installed. Also added environment var if
  you need to disable it, even when it is installed.
+ (API) Actions can now post sources as “late results”. (*Get Notes Search
  Results...* now uses this.)
+ (API) Add ``ShowHide``, ``ShowHideOnDisplay`` to D-Bus interface.

+ Plugins

  + In *Notes*, retry opening notes for slow activation in Gnote/Tomboy
  + Fix task sort order in *Getting Things GNOME*
  + *Rhythmbox* and *Notes* refresh more often (when their programs restart)

kupfer v310
-----------

+ Speed up ranking objects a bit when the catalog is large
+ Show a nicer message when no action matches the search
+ Using AppIndicator is now an option (and optional dependency)
+ Plugins:

  + Add *Firefox Keywords* to use configured keywords as search engines
  + In *Applications* show more apps in *Open With...*
  + In *Applications* add new action *Reset Associations*
  + Reintroduce the *Rhythmbox* plugin, which allows searching the library,
    playing and enqueuing songs. General Play/Pause/Prev/Next is in
    the *Media Player Control* plugin already.
  + Reintroduce the *Getting things GNOME* plugin.
  + Reintroduce the *Devhelp* plugin.

+ (API) Allow Sources and TextSources to customize their no match and
  waiting for search text.
+ (API) Allow Actions to use both the catalog and an extra source for the
  indirect object

kupfer v309
-----------

+ Change Kupfer's D-Bus name and interface and object path. The old names
  are still active, but the migration period will be very short because we
  are in a rapid change phase. New names use the domain ``io.github.kupferlauncher``.
+ Change the no match icon to use transparency instead of ugly pixelation
+ Change the default text to simply be *Type to search*, which is shorter
  and simpler.
+ Folding of *ß* has been restored, so that a search for *ss* will match it.

+ Plugins:

  + In *Notes*, some actions are now asynchronous and/or have better error
    reporting.
  + In *Notes*, update for kzrnote 0.2
  + Enable *Quicksilver Icons* by default

kupfer v308.2
-------------

+ Fix showing the result list in KWin (#47) with a specific workaround
+ Plugins:

  + Fix *Shell Commands* so that they inherit the parent environment
  + Remove *GNOME Session Management* from the set enabled by default

kupfer v308.1
-------------

+ Fix widget style/space issue that was especially apparent in the GTK theme
  Adapta.

kupfer v308
-----------

Be sure to check out the settings in the *Applications* plugin in this
release. The web site now also shows a language selection for the user’s
guide, so that the translations are readily available.

+ Fix a slight wobble in the result list’s position by making sure the
  description label stays the same size
+ Fix how the star and arrow at the right side of the result list line up
+ Plugin API: Add methods ``get_gfile`` and ``is_content_type`` to ``FileLeaf``
+ Prerender and install fixed icon sizes
+ Plugins:

  + In *Applications* change how it filters applications based on desktop
    type. The new default desktop type is blank, and this should pick up
    the right desktop environment automatically. Make the *Use Desktop
    Filter* toggle actually work.
  + Speed up recent documents slightly by caching an intermediate result
  + In *Documents* also recognize more file extensions when sorting
    libreoffice documents to the right app.
  + Remove action *Send in Email To* from *Default Email Client*, since it
    is unlikely to work for the default ``mailto:`` URL handler.
  + Rename the remaining action *Compose Email* → *Compose Email To* in
    default mail, for consistency.

kupfer v307
-----------

Released Wednesday, 15 feb 2017

+ Fix a bug with disambiguation of action names
+ Stop merging contacts by full name equality
+ Accept dropped text and files on Kupfer’s window
+ Fix API to not ask for content-decoration of a leaf with existing content
+ Plugins

  + Reintroduce *Pidgin*
  + Reintroduce *Shorten Links*
  + In *Thunderbird*, rename compose email actions to differentiate them,
    *Compose Email To*, *Compose Email With*.
  + In *Image Tools*, show an error if ``jpegtran`` is not found
  + In *Audacious* add runnable item *Show Playing*
  + Fix *Wikipedia* to use https
  + In *Documents*, match more applications to their own recent documents,
    notably LibreOffice
  + Run copy from *File Actions* asynchronously
  + Add a new help page, for plugin *Thunar*

kupfer v306
-----------

Released Monday, 13 feb 2017

+ Fix a compatibility issue with waf wscripts for non UTF-8 locales
+ Fix plugin info loading from .zip files.
+ Fix exception on filenames that could not be represented in unicode. They
  are silently skipped in directory listings for now.
+ Plugins:

  + Fix *Deep Archives* to skip directories named with archive extensions
  + Fix ``=help`` in *Calculator*
  + Revert the hack that replaced ``,`` with ``.`` in numbers in
    *Calculator*
  + Add file action *Attach in Email To...* in *Thunderbird*
  + Add text action *Compose Email* in *Thunderbird*
  + Fix *Thunderbird* to read unicode correctly from the address book.
  + Reintroduce places (GTK bookmarks) in *Documents*

kupfer v305
-----------

Released Saturday, 11 feb 2017

+ Tweak how the selected pane is drawn. We still haven't arrived at a theme
  and color-independent way to do this; Gtk 3 drawing and styling knowledge
  is welcome in github.
+ Fix some drawing bugs in the main kupfer window by removing some old
  erronous overrides of the widget size calculation.
+ Add attribute ``source_use_cache`` to the API for sources
+ Plugins:

  + Add new plugin *Media Player Control* for basic control of any
    mpris-capable player. This plugin is experimental.
  + Fix bugs in *Volumes* so that it works well under Gtk 3
  + Fix the Copy button in the *Show Text* result. The text is also now
    editable.
  + *Applications* now only proposes apps in *Open With...* that support
    opening files. (Add ``%U`` or similar to your application’s command line
    in the .desktop file, if it's missing.)
  + Stop enabling *File Actions* by default (copy is not async with Gtk 3
    so it is now defective). Please use the Thunar file actions instead.

kupfer v304.1
-------------

Released Thursday, 9 feb 2017

+ Plugins:

  + *Clipboard:* add back *Clipboard Text* that was removed in v304 by
    mistake

kupfer v304
-----------

Released Wednesday, 8 feb 2017

+ Clean up the distributable tarball; extra content like oldplugins is now
  only in the repository and not in the tarball.
+ Fix double-clicking on the Kupfer window
+ Increase default result list length slightly
+ Plugins:

  + Reintroduce *Firefox Bookmarks*
  + *Clipboard:* attempted fix for a reported stack overflow
  + *Clipboard:* reintroduce *Clipboard File(s)* proxy object
  + Fix *File Actions* so that it works (for Gtk 3)

kupfer v303
-----------

Released Tuesday, 7 feb 2017

GNOME's hosting of the project is now officially at an end; mailing list and
repo there are gone, we are on github now. Thank you GNOME and see you next
time!

+ Completed port to pygi by removing ``pygtkcompat``
+ Build config will now look for ``python3`` if ``python`` is too old.
+ Plugins:

  + Reintroduce *Locate*

kupfer v302
-----------

Released Monday, 6 feb 2017

+ Fix sending files from the command line
+ Fix installation of help pages, new standard location ``/usr/share/help``
  and including a file that was missing.
+ Fix --list-plugins and update man page.
+ Patch the included waf so that it now builds using Python 3
+ Plugin *Applications*: Add MATE as alternative
+ Fix interface to not draw preedit field at all
+ Fix *Copy to Clipboard* action.

kupfer v301
-----------

Released Monday, 6 feb 2017

A new decade of Kupfer

+ Fix loading plugin list for Python 3.6
+ New: ? starts free text input
+ New: ? text prefix gets live full text search results (plugin Tracker)
+ Plugins

  + reintroduce tracker
  + fix audacious
  + fix dictionary
  + drop multihead (updated, but needs testing)
  + drop gnome-terminal (obsolete)

kupfer v300
-----------

Released Sunday, 5 feb 2017

A new decade of Kupfer dawns!

+ Port Kupfer to Python 3
+ Port Kupfer to Gtk 3 and GObject Introspection
+ Reindent the codebase to 4 spaces

+ Regard this release as a preview, it may have bugs
+ We have a github organization, new webpage, and will need maintainers to
  hold the wheel into the next decade

+ Breaking changes:

  + Plugin configs are reset
  + Old ``kfcom`` can no longer be parsed
  + Some changes in the Plugin API
  + Many plugins are obsolete and have been dropped. Some old plugins can be
    updated, but I in general Kupfer wants to explore new kinds of
    interaction, and not necessarily collect all possible plugins in-tree
  + Gtk theming has changed

+ New features:

  + Use CSS for Gtk 3 themes
  + Implemented using 2010s technology

+ Dependencies:

  + This release requires ``Keybinder-3.0`` (using G-I), that will be
    relaxed later

.. role:: lp(strong)

kupfer v208
-----------

Released Friday,  1 June 2012

* Fix bug with nonexisting catalog directories (Karol) (:lp:`1000980`)
* Fix sending to many with Thunderbird (Karol) (:lp:`955100`)
* Fix history file for OpenOffice/LibreOffice (Karol)
* *Audacious* plugin: Work with Audacious 3 (Ulrik)

* Localization updates:

  + cs, Marek Černocký
  + es, Daniel Mustieles
  + fr, Alexandre Franke, Bruno Brouard
  + ru, Nikolay Barbariyskiy
  + sl, Matej Urbančič


kupfer v207
-----------

Released Sunday, 26 February 2012

* Documentation translated to French by Bruno Brouard
* New translation to Brazilian Portuguese by Djavan Fagundes
* New translation to Hungarian by SanskritFritz
* Handle large text objects a bit better
* Introduce proxy objects *Clipboard File* and *Clipboard Text*. These
  objects are implemented in the *Clipboard* plugin, just like the *Selected
  Text* object which has changed home to this plugin. Accordingly,
  deactivating the clipboard plugin will deactivate these proxies.
* Support copying and pasting files from/to the clipboard, which allows much
  easier integration with file managers.
* Add an information text detailing which keyring backend is used to store
  passwords, visible in the user credentials dialog.
* *Vim:* Expand the vim plugin to use a helper process to track running
  server instances of (G)Vim. Each running session is exported as an object,
  and most importantly, files can be opened in a session using the action
  *Open With*.
* *Multihead Support:* This new plugin will start the "keyboard shortcut
  relay" service on additional screens, if it is needed. It is active by
  default, and does not do anything on configurations with a single
  X screen.
* *Send Keys:* Allow sending key sequences using comma trick.
* *Thunar:* Add action *Symlink In...*
* *Quicksilver Icons:* New plugin with a few icons from Quicksilver
* Use themable custom icon names ``kupfer-execute``, ``kupfer-catalog``,
  ``kupfer-launch``. Also allow plugins to choose to supply icons when the
  icon theme lacks them, or always override the icon theme.
* Fix passing zero-length arguments to programs (Fabián Ezequiel Gallina)
  (:lp:`863349`)
* *Gmail:* Expose more contact info fields (Adi Sieker, Karol Będkowski)
* Add plugin *DuckDuckGo* (Isaac Aggrey)
* Add quick note action to *Zim* (Karol Będkowski)
* Add *Edit Contact in Gmail* to *Gmail* (Karol)
* Fix version detection in *Gajim* (Karol)
* *Google Translate:* Since Google no longer provides this API (for free),
  this plugin is no longer included in Kupfer.
* Fix compatibility with dbus-python version 1.0 (:lp:`921829`)
* Fix loss of window shape when centering (David Schneider) (:lp:`779845`)
* We are now using the format .tar.xz for the distribution tarball.
* The git repository and tarball now includes a local copy of waf (1.6.11),
  unmodified but with unused in Tools/ and extras/ removed.

* Localization updates:

  + (cs) Marek Černocký
  + (de) Mario Blättermann
  + (fr) Bruno Brouard
  + (es) Daniel Mustieles
  + (hu) SanskritFritz
  + (pl) Piotr Drąg
  + (pt_BR) Djavan Fagundes
  + (sl) Andrej Žnidaršič
  + (sv) Ulrik


kupfer v206
-----------

`The longest changelog ever—the best Kupfer ever?`:t:

Released Thursday, 14 April 2011

These are changes since the v205 release. Below this I have included, the
full changelog for all the features introduced in v205, since it was not
published in whole together with the v205 release.

I would like to thank all contributors for patches, bug reports, comments
and translations. A special thanks to those who have contributed to the
`user documentation`__; it is now complete in both Polish and Spanish.

If you like my work with Kupfer, you can support me by donating. There are
instructions how to do so on the web page. –ulrik.

__ http://kaizer.se/wiki/kupfer/help/

* *Thunderbird:* fix double create email windows (:lp:`747198`)
* *Thunderbird:* fix problem with loading contacts (Karol Będkowski)
  (:lp:`747438`)
* Use ``rst2man`` as it was configured (:lp:`747500`)
* Reduce runtime memory use for substantially by reimplementing the icon
  cache (expectations vary btw. 10 to 30 percent).
* Prefer gnomekeyring over kwallet, and don't load keyring support if it is
  not requested by a plugin (:lp:`747864`)
* Make the "folder" icon take precedence over "inode/directory"
* Fix a regression in *Go To* that would not focus minimized windows.
* In *Go To* action, cycle application windows (if they are all on the same
  workspace).
* Fix :lp:`671105`: the user's home is aliased as *Home Folder* and the
  "lookalike" application is hidden.
* Use GTK+ as default icon set, the ASCII icon set remains as a plugin
* Fix regression :lp:`749824`, kupfer used a GTK+ 2.20 feature. Kupfer
  should now run under GTK+ 2.18 (2.16?). GTK+ 2.20 is recommended and
  needed for full input method support.
* Remake ``.desktop`` file parsing to be much more lenient, so that we
  can launch all applications again. Affected were especially launcher files
  written by wine.
* Make sure the ``Home`` key works in text mode (:lp:`750240`)
* *Rhythmbox:* Fix omission of ``.jpg`` extension when searching cover art
  (William Friesen)
* Support xfce4-dict in *Dictionary* plugin (David Schneider)
* Make sure ``kupfer.svg`` can be mimetype-detected (NAKAMURA Yoshitaka)
  (:lp:`750488`)
* Fix regression that prevented mimetypes and icon cache from being updated
  properly when installing from source.
* Focus the plugin list search box by default in the preferences window.
* Fix regression in *XFCE Session Management* that had a broken logout
  command.
* Install kupfer as a Thunar 'sendto' object.
* Fix a bug in the autostart file we installed, it was including a '%F'
  which broke ``--no-splash`` when autostarted on XFCE.
* *LibreOffice:* support their newer recent documents file (Karol Będkowski)
* *Notes:* Insert newlines after the new note title (:lp:`748991`)
* *Commands:* Recognize absolute paths with arguments as shell commands (for
  example ``/bin/grep --help``. (:lp:`152093`)
* *GNU Screen:* check if sessions are still active (:lp:`756449`), don't
  give up even if ``$SCREENDIR`` is missing when we are started
  (:lp:`753376`)
* *Notes:* support the program kzrnote as well
* Renamed the two like-named command actions in spanish (Daniel Mustieles)
 
* Localization updates for v206:

  + sl Andrej Žnidaršič
  + es Daniel Mustieles
  + de Mario Blättermann

This is the changelog for the v205 release, which was released previously.

* Changes to the interface

  + Add a small menu button on the window for explicit access to
    context actions, preferences window, and help.
  + Increase icon size to 128px
  + Always show description field
  + Use an undecorated window with rounded corners
  + Let the frame be slightly transparent if supported
  + Themable colors and properties by using GTK+ styling, see
    ``Documentation/GTKTheming.rst``, and the plugin *Custom Theme* that
    shows how to use custom styles.

* Add context action "Set X as default action for object Y"

  + For example, you can make *Launch Again* default for Terminal, and our
    default configuration uses this setting for two common terminals (GNOME
    and XFCE).

* Updated Kupfer's technical documentation (in ``Documentation/``),
  including the Plugin API reference.

* Implement a preedit widget for input methods, also resolving
  the incompatibility with ibus (David Schneider) (:lp:`696727`)

* Re-implement launching of applications

* Allow the user to configure which terminal program is used.
  Applies to all of *Run in Terminal*, *Open Terminal Here*, for .desktop
  files that specify ``Terminal=true`` etc.

* Implement an "alternatives" mechanism so that plugins can
  register mutually exclusive alternatives. Currently implemented
  are Terminals (see above) and Icon Renderers.

* *Thunar*: Use Thunar 1.2's Copy and Move API.

  + These allow copying and moving anything through thunar, and it will
    show progress dialogs for longer transactions.

* Add *Ascii & Unicode Icon Set* for fun

* Add simple plugin *Quick Image Viewer* to show images in a simple way.

* Add *Send Keys* plugin that can send synthetic keyboard events,
  and prominently can be used for the *Paste to Foreground Window*
  action on text. Requires ``xautomation`` package. (:lp:`621453`)

* *Volumes:* treat mounts as regular folders, so they can be targets for
  file operations.

* *File Actions:* the action *Move to Trash* switches home to the *Trash*
  plugin, the archive actions go to new *Archive Manager* plugin. *Archive
  Manager* also updated to recognize more archive file types, including
  ``.xz``.

* Activate current selection on double-click in the interface.
  (:lp:`700948`)

* Update the preferences window and move the folder configuration to the
  Catalog tab.

* Add ``initialize_plugin`` to the plugin interface.

* The D-Bus interface has been extended with X screen and timestamp-aware
  versions of all methods:

  + ``PresentOnDisplay``, ``PutFilesOnDisplay``, ``PutTextOnDisplay``,
    ``ExecuteFileOnDisplay``  all act like their similarly-named
    predecessors, but take ``$DISPLAY`` and ``$DESKTOP_STARTUP_ID`` as their
    last two arguments.

  + ``kupfer-exec`` activation sends the event timestamp so that focus can
    be carried along correctly even when running ``.kfcom`` files (if
    activated as an application by startup-notification-aware launchers,
    this works with most standard desktop components).

* Internally, change how actions are carried out by allowing the
  action execution context object to be passed down the execution chain
  instead of being a global resource. This also allows plugins to cleanly
  access current environment (event timestamp, current screen etc).

  + Support running kupfer on multiple X screens (:lp:`614796`), use
    the command ``kupfer --relay`` on each additional screen for global
    keyboard shortcut support. This is experimental until further notice!

* The *Tracker 0.8* plugin supports version 0.8 and 0.10 alike. Because of
  that and the expected compatibility with one version after this too, it's
  now called *Tracker*.

* The *Favorites* plugin lists *Kupfer Help* and *Kupfer Preferences* by
  default (for new users), so that it's not empty and those items are ranked
  higher.

* In free-text mode, show a character count in the text entry.

* The action *Go To* on applications has changed implementation. It will
  first bring to front all the application's windows on the current
  workspace, and upon the next invocations it will focus the other
  workspaces, in order, if they have windows from the same application.  For
  single-window applications, nothing is changed.
 
* Localization updates for v205:

  + (cs) Marek Černocký
  + (de) Mario Blättermann
  + (es) Daniel Mustieles
  + (ko) Kim Boram
  + (nb) Kjartan Maraas
  + (pl) Karol Będkowski
  + (sl) Andrej Žnidaršič
  + (sv) Ulrik


kupfer v205
-----------

Congratulating ourselves

Released Friday, 1 April 2011

* Changes to the interface

  + NOw we have a teh awsum interface

* Add context action "Set X as default action for object Y"

  + You can finally make Kupfer do what you want.

* Implement a preedit widget for input methods, also resolving
  the incompatibility with ibus (David Schneider) (:lp:`696727`)

  + Ok, so that foreign people can enter text too.

* Updated Kupfer's technical documentation (in ``Documentation/``),
  including the Plugin API reference.

  + Someone finally bothered

* The action *Go To* on applications has changed implementation. It will
  first bring to front all yada yada, etc...

  + Whatever, it finally works in a sensible way

* And tons of other stuff, enjoy!


kupfer v204
-----------

Released Friday, 18 March 2011

* Expand and improve upon `Kupfer's User Documentation`__.
* Use and require **Waf 1.6**, which supports building using either Python 3
  or Python 2.6+. Kupfer itself still uses Python 2.6+ only.
* Add *Gwibber* plugin that allows integration with Twitter, Identi.ca, Buzz
  etc. (Karol Będkowski)
* Add chat client *Empathy* plugin (Jakh Daven)
* Remove the plugin *Twitter* since it is incompatible and has no updated
  implementation.
* Add *Show QRCode* plugin by Thomas Renard (:lp:`611162`)
* Periodically save data from plugins so it's not lost if Kupfer can't exit
  cleanly at logout
* *Commands*: Add actions *Pass to Command*, *Filter through Command*, *Send
  to Command* which add a lot of shell script-related power to Kupfer.
  These actions, and *Run (Get Output)* as well, use a shell so
  that you can run shell pipelines.
* *Search the Web*: Fix bug in OpenSearch parser (:lp:`682476`)
* *VirtualBox*: Support vboxapi4 (Karol Będkowski)
* *Thunderbird*: Fix problems in the mork parser (Karol Będkowski)
  (:lp:`694314`)
* *OpenOffice*: Support LibreOffice too (Karol Będkowski)
* Fix "Y2011 bug" where the time parameter overflowed INT32 in keybinder
* *Shorten Links*: Use only services with stable API, added and removed
  services.
* *Google Search*, *Google Translate* and ``bit.ly`` in *Shorten Links* can
  use SSL for transport if a third-party plugin is installed.
* Fix bug if evolution address book is missing (Luca Falavigna)
  (:lp:`691305`)
* Fix *Search the Web* to use localized ``firefox-addons`` subdirectories
  for search engines (:lp:`735083`)
* Fix bug with integer division (Francesco Marella)
* *APT:* Workaround bug with ``subprocess`` (:lp:`711136`)
* Find cover art files just like Rhythmbox (William Friesen) (:lp:`676433`)
* Use ``readlink`` in ``kupfer-exec`` script too since ``realpath`` is not
  always available.
* Allow plugins to use update notifications (William Friesen)
* Bug :lp:`494237` is hopefully fixed once and for all.
* The *Large Type* action will work with anything that has
  ``TextRepresentation``

__ http://kaizer.se/wiki/kupfer/help/

* Localization updates:

  + (cs) Marek Černocký
  + (da) Joe Hansen
  + (de) Mario Blättermann
  + (es) Daniel Mustieles
  + (gl) Marcos Lans
  + (pl) Karol Będkowski
  + (sl) Andrej Žnidaršič
  + (sv) Ulrik
  + (zh_CN) Aron Xu, Yinghua Wang

kupfer v203
-----------

.. role:: git(emphasis)

Released Saturday,  6 November 2010

* Center Kupfer on the monitor were the mouse pointer is (:lp:`642653`,
  :git:`3d0ba12`)
* Ignore the system's configured input manager by default (User can choose
  by pressing Shift+F10 in Kupfer). Kupfer is still not compatible with
  ibus 1.3. (:lp:`601816`, :git:`4f029e6`)
* Use ``readlink`` instead of ``realpath`` (:git:`656b32d`)
* *Opera Mail*: Handle contacts with multiple e-mail addresses (Chris
  Parsons) (:lp:`661893`, :git:`12924be`)
* *Google Translate*: Fix language list (Karol Będkowski) (:lp:`600406`,
  :git:`7afac2b`)
* *TSClient*: Search recursively for session files (Karol, Freddie Brandt)
  (:git:`ad58c2e`)
* *Rhythmbox*: Fix thumbnail lookup (William Friesen) (:lp:`669077`,
  :git:`b673f98`)
* New Slovenian translation of help by Matej Urbančič (:git:`3b7df25`)
* New Turkish translation by M. Deran Delice (:git:`bd95d2a`)

kupfer v202
-----------

Released Sunday,  5 September 2010

* Add option to hide Kupfer when focus is lost (and enable by default)
  (Grigory Javadyan) (:lp:`511972`)
* Use application indicators when available (Francesco Marella)
  (:lp:`601861`)
* Python module `keyring` is now optional for Kupfer (but required for
  the same plugins that used them before)
* Update *Google Translate* for protocol changes (Karol, Ulrik) (:lp:`600406`)
* Disable saving window position until a better solution is found
* Use 'mailto:' as URL (:lp:`630489`)
* Fix UI glictch with empty Source (William Friesen) (:lp:`630244`)
* Small changes (Francesco Marella)
* New Czech translation of the help pages (Marek Černocký)
* New Italian translation of the help pages (Francesco Marella)
* New Polish translation of the help pages (Karol Będkowski)
* New Basque translation (Oier Mees, Iñaki Larrañaga Murgoitio)
* New Galician translation (Fran Diéguez)

* Localization updates:

  + cs (Marek Černocký)
  + de (Mario Blättermann)
  + pl (Karol Będkowski)
  + sl (Andrej Žnidaršič)
  + zh_CN (Aron Xu)


kupfer v201
-----------

Released Wednesday, 30 June 2010

* New Logo and Icon by Nasser Alshammari!
* New plugin *Opera Mail* by Chris Parsons
* New plugin *SSH Hosts* by Fabian Carlström
* New plugin *Filezilla* by Karol Będkowski
* New plugin *Getting Things GNOME!* (Karol)
* New plugin *Vim* (recent files)
* *Clipboard:* Option *Copy selection to primary clipboard* (Karol)
* *Firefox:* Option *Include visited sites* (Karol) (:lp:`584618`)
* *Thunar:* Action *Send To...* (Karol)
* New preferences tab for Catalog configuration
* Allow disabling and "unloading" plugins at runtime
* Support new tracker in plugin *Tracker 0.8*
* *Shell Commands:* New Action *Run (Get Output)*
* New plugin capabilities: ActionGenerator, Plugin setting change
  notifications (Karol)
* Use ``setproctitle`` module if available to set process title to
  ``kupfer`` (new optional dependency)
* Don't use a crypted keyring (partially addresses :lp:`593319`)
* Fix :lp:`544908`: Retain window position across sessions
* Fix :lp:`583747`: Use real theme colors for highlight
* Fix :lp:`593312`: About window has no icon
* More minor changes

* Localization updates:

  + cs, Marek Černocký
  + de, Mario Blättermann
  + es, Jorge González
  + it, Francesco Marella
  + pl, Karol Będkowski
  + sl, Andrej Žnidaršič
  + sv, Ulrik

kupfer v200
-----------

Released Wednesday,  7 April 2010

* Add Keyboard Shortcut configuration (Karol Będkowski)
* Make it easier to copy and move files (William Friesen), while showing
  user-friendly errors when action is not possible (Ulrik) (:lp:`516530`)
* Collect results in a *Command Results* subcatalog, including results from
  asynchronous commands (Pro tip: Bind a trigger to *Command Results* →
  *Search Contents*, for quick access to copied files, downloaded files etc)
* *Last Result* proxy object implemented
* Add *Cliboards* -> *Clear* action (Karol)
* Add *Rescan* action for some sources (Karol)
* Add an icon in the plugin list search field to enable clearing it (Karol)
* Fix spelling (Francesco Marella)
* Fix bug `544289`:lp:
* Require python module ``keyring`` (since pandoras-box-1.99, but was not
  mentioned)
* Recommend python-keybinder version 0.0.9 or later

* Localization updates:

  + cs Marek Černocký
  + de Mario Blättermann
  + es Jorge González
  + pl Karol Będkowski
  + sl Andrej Žnidaršič
  + sv Ulrik
  + zh_CN Aron Xu

kupfer version pandoras-box-1.99
--------------------------------

Released Tuesday, 16 March 2010

* Plugins can be loaded at runtime, although not unloaded can they not
* Plugins can bundle icons, and plugins can be packaged in .zip files
* New plugins *Google Search*, *Textfiles* and *Thunar*
* New plugin *Deep Archives* to browse inside .zip and .tar files
* New plugins *Twitter*, *Gmail* and *Google Picasa* by Karol Będkowski
* New plugin *Evolution* by Francesco Marella
* New action *Get Note Search Results...* in *Notes* by William Friesen
  (LP#511954)
* New plugin capabilities (user credentials, background loader) by Karol
* Added *Next Window* proxy object to *Window List* plugin
* Allow saving Kupfer commands to .kfcom files, and executing them with
  the ``kupfer-exec`` helper script.
* Display error notifications to the user when some actions can not be
  carried out.
* Allow collecting selections with the *Clipboard* plugin (Karol)
* Include Gnome/Yelp documentation written using Mallard (Mario Blättermann)

* Make *Zim* plugin compatible with newer Zim (Karol, Ulrik)
* Detect multiple volume rar files (William Friesen) (LP#516021)
* Detect XFCE logout better (Karol) (LP#517819)
* Fix reading VirtualBox config files (Alexey Porotnikov) (LP#520987)
* Fixed module name collision in user plugins (LP#518958), favoriting "loose"
  applications (LP#518908), bookmarked folders description (LP#509385),
  Locate plugin on OpenSUSE (LP#517819), Encoding problem for application
  aliases (LP#537730)
* New French translation by Christophe Benz
* New Norwegian (Bokmål) translation by Kjartan Maraas

* Kupfer now requires Python 2.6

* Localization updates:

  + cs Marek Černocký
  + de Mario Blättermann
  + es Jorge González
  + fr Christophe Benz
  + it Francesco Marella
  + nb Kjartan Maraas
  + pl Karol Będkowski
  + pt Carlos Pais
  + sl Andrej Žnidaršič
  + sv Ulrik


kupfer version pandoras-box-1.1
-------------------------------

Released Monday,  8 February 2010

* Fix bug in contact grouping code that could cause unusable Kupfer with Pidgin
  plugin. Reported by Vadim Peretokin (LP#517548)
* Chromium plugin will index Google Chrome bookmarks as fallback, by William
  Friesen (LP#513602)
* Kupfer's nautilus plugin was changed to be easier to reuse for others
* Some minor changes

* Localization updates:

  + pt (Carlos Pais)


kupfer version pandoras-box-1
-----------------------------

"Pandora's box"

Released Monday, 1 February 2010

* Implement the famous "comma trick": Press , (comma) in the first or
  third pane to make a stack of objects to perform actions on. This allows
  actions on many objects and even many-to-many actions.
* New plugin: *Triggers*: Add global keybindings to any command you can
  perform in Kupfer.
* New plugin *Skype* by Karol Będkowski
* New plugin *Thunderbird* (or Icedove) (Karol)
* Implement merging of contacts and hosts: All contacts of the same name are
  merged into one object. (Karol, Ulrik)
* New plugin *Higher-order Actions* to work with saved commands as objects
* The *Favorites* plugin was reimplemented: you may favorite (almost) any
  object. Favorites get a star and a rank boost.
* *Window List* plugin was improved, most notably a *Frontmost Window* proxy
  object was added
* New proxy object *Last Command*
* The *Firefox* plugin now includes most-visited sites from browser history
  (William Friesen, Karol, Ulrik)
* The list of plugins has a field to allow filtering the list (Karol)
* New Czech localization by Marek Černocký
* Many smaller changes.

* Localization updates:

  + cs (Marek Černocký, Petr Kovar)
  + de (Mario Blättermann)
  + nl (Martin Koelewijn)
  + pl (Karol)
  + sv
  + sl (Andrej Žnidaršič)

kupfer version c19.1
--------------------

Released 31 December 2009

* New plugin: *Shorten Links* by Karol Będkowski
* Implemented *Ctrl+C* (and *Ctrl+X*) to copy (cut) selected object
* Fix bug LP #498542: restore window position code to c18
* Partial fix of bug LP #494237, window is sometimes blank
* Fix bug LP #500395, column order in *Top* plugin (Karol)
* Fix bug LP #500619, handle network errors in *Google Translate* plugin
  (Karol)

* Localization updates:

  + pl (Karol)
  + sv

kupfer version c19
------------------

Released 18 December 2009

* New plugins:

  + *Gnome Terminal Profiles* by Chmouel Boudjnah
  + *OpenOffice* recent documents in OpenOffice by Karol Będkowski
  + *Top* show and send signals to running tasks (Karol)
  + *Truecrypt* show volumes in truecrypt history and allow mounting them
    (Karol)
  + *Vinagre* Remote Desktop Viewer (Karol)
  + *XFCE Session Management* (Karol)
  + *Audacious* by Horia V. Corcalciuc

* New Slovenian translation by Andrej Žnidaršič
* Some plugins will now explicitly require a D-Bus connection and fail to
  load if no connection was found.
* Add accelerators *Page Up*, *Page Down* and *Home* in the result list.
  (Karol)
* Use customized or localized desktop directory instead of hardcoding
  ``~/Desktop`` by default. It will not affect users who already customized
  which directories Kupfer indexes.
* It now is possible to favorite shell commandlines
* *Gajim* plugin now works with version 0.13 (Karol) (LP #489484)
* Basic support for Right-to-left (RTL) interface
* Fix bugs with "loose" Applications (not in system directories), reported
  by Chmouel.
* Add accelerator *Ctrl+Return* for **Compose Command**: You may compose a
  command object out of an (Object, Action) combination, to be used with the
  new action *Run After Delay...*.
* Added file action *Send by Email* to *Claws Mail* plugin (Karol)
* Added file action *Mount as TrueCrypt Volume* to *TrueCrypt* plugin (Karol)
* Many small bugfixes

Localization updates:

* de: Mario Blättermann
* es: Jorge González
* it: Francesco Marella
* pl: Karol Będkowski
* sl: new (Andrej)
* sv: Ulrik Sverdrup

kupfer version c18.1
--------------------

Released 20 November 2009

* Fix bug to toss out malfunctioning plugins properly (Reported by Jan)
* Fix bug in showing the shutdown dialog, reported by user sillyfofilly (LP
  484664)
* Fix bug in plugin *Document Templates*, reported by Francesco Marella
  (part of LP 471462)

kupfer version c18
------------------

Released 18 November 2009

"Mímisbrunnr"

* New plugins:

  + *Pidgin* by Chmouel Boudjnah
  + *Google Translate* by Karol Będkowski
  + *APT* (package manager APT) by Martin Koelewijn and Ulrik
  + *Document Templates*
  + *Kupfer Plugins*
  + *Show Text*

* *Gajim* plugin matches contacts by jid as well as name, suggested by
  Stanislav G-E (LP 462866)
* Action *Rescan* on sources is now debug only (should not be needed)
* Kupfer installs its Python package into ``$PREFIX/share`` by default,
  instead of installing as a system-wide Python module.
* Kupfer can take input on stdin and pass as text to an already running
  instance
* Fix bug in *Services* for Arch Linux, reported by lh (LP 463071)

* Changes for plugin authors:

  + May use ``uiutils.show_text_result`` to show text
  + ``kupfer.task.ThreadTask`` is now a reliable way to run actions
    asynchronously (in a thread)
  + You can use item *Restart Kupfer* to restart (in debug mode)
  + Plugins may be implemented as Python packages, as well as modules

* Updated the dependencies in the README. pygobject 2.18 is required. Added
  gvfs as very recommended.
* Other bugfixes

Localization updates:

* de (Mario Blättermann)
* es (Jorge González)
* nl (Martin Koelewijn)
* pl (Karol Będkowski)
* sv
* zh_CH (lh)

kupfer version c17
------------------

Released, 25 October 2009

"A fire lit by nine kinds of wood"

* 8 new plugins by Karol Będkowski:

  + *Claws Mail*, Contacts and actions
  + *Gajim*, Access to gajim contacts
  + *Opera Bookmarks*, for the web browser Opera
  + *PuTTY Sessions*, access to PuTTY sessions
  + *System Services*, start, stop or restart system services
  + *Terminal Server Client*, access to TSClient sessions
  + *VirtualBox*, control virtual machines, Sun or OSE version
  + *Zim*, access pages in the desktop wiki

* New plugin *Chromium Bookmarks* by Francesco Marella
* Plugins missing dependencies will be presented in the GUI with a clear
  error message.
* *Firefox Bookmarks* plugin: Workaround Firefox 3.5 writing invalid JSON
  (Karol, Ulrik)
* *Locate* plugin: Ignore case by default, add option to control this.
  (Karol)
* Kupfer is much more friendly and says "Type to search in *Catalog*" when
  it is ready to be used.

* Localization updates:

  + New Simplified Chinese localization (lh)
  + New Dutch localization (Martin Koelewijn)
  + New Portuguese localization (Carlos Pais)
  + Updated pl (Karol)
  + Updated es (Jesús Barbero Rodríguez)


kupfer version c16
------------------

Released 5 October 2009

* Translation to German (Thibaud Roth)
* Polish translation updated (Maciej Kwiatkowski)
* Add search engine descriptions from ``firefox-addons`` (Francesco Marella)
* Speed up directory browsing by using much less system calls
* Improve documentation and put it together into a `Manual`.
* Generate man page from reStructuredText document `Quickstart`.
* Evaluate valid actions (per object) lazily to save work.
* Add accelerators *Ctrl+Q* (select quit) and *Alt+A* (activate)
* Parse even horribly wrong search engine descriptions (Bug reported by
  Martin Koelewijn)


kupfer version c15
------------------

* Translation to Polish by Maciej Kwiatkowski
* Speed up the string ranker tremendously; 3x faster in common cases.
* All objects now have an alias in the basic latin alphabet (if possible) so
  that, for example, query `wylacz` matches item *Wyłącz*.
* Show notification icon by default
* Read XML with cElementTree (Faster.)
* Read Firefox 3's bookmarks (Python2.5 requires `cjson` module)
* New Plugin: Image Tools, with action *Scale...* and JPEG rotation actions
  (*Scale* requires ImageMagick (`convert`), JPEG actions `jpegtran` and
  `jhead`)
* Basic support for a Magic Keybinding: summon kupfer with current selection

kupfer version c14.1
--------------------

* Fix two bugs with new browisng mode (soft reset for text mode, backspace or
  left to erase a subcatalog search)

kupfer version c14
------------------

* Rewrite and improve browsing mode:

  * Browsing the catalog or folders is much improved; it is easier to keep the
    overview and be oriented.
  * Returning to kupfer after having performed an action, the old object is
    still available, but without locking the catalog to its location.
    When spawning kupfer again, the previous context is available if you
    immediately browse; if you search, you search the whole catalog.
  * The search times out after 2 seconds if no key is typed. Now the highlight
    text will fade to show this.

* Add accelerators `Ctrl+G` and `Ctrl+T` to get current selection in nautilus
  and currently selected text (if available).

kupfer version c13.1
--------------------

* Fix two bugs with *Rename To...* 

kupfer version c13
------------------

* New Plugin: Calculator
* New Action: *Rename To...* in File Actions Plugin
* Smaller changes (Stop learned mnemonics database from growing indefinitely,
  Catch SIGINT without python's handler, *Copy To...* requires pygobject 2.18
  now)

kupfer version c12
------------------

* Translation to Spanish by Leandro Leites
* Preferences. Display plugin settings and options beside the plugin list,
  and allow configuring included (and watched) directories.
* Support the new Gnome session protocol to save state on log out.
* Improve embarassingly bad shell command quoting for *Execute* and Tracker tag
  actions.
* Specify user data locations with `X-UserData`
* Fix an AttributeError in Notes plugin reported by Francesco Marella
* Smaller fixes (Add/remove favorite could cease to work, Track intantiated
  sources better)

kupfer version c11
------------------

The "this one goes to 11" release

* New plugin: Notes (Gnote and Tomboy support)

  * Access notes, Actions: *Create Note* and *Append to Note...*

* New plugin: Selected File

  * Kupfer ships with a Nautilus python extension that once installed,
    you can access the currently selected file in Nautilus from Kupfer,
    as the *Selected File* object

This release is localized in: Swedish (100%), Italian (90%)

kupfer version c10.1
--------------------

* Spanish Translation by Leandro Leites

kupfer version c10
------------------

* Updated italian localization
* New plugins: Url Actions, Web Search (rewritten to use all Firefox' search
  engines)
* New actions: *Set Default Application*, *Create Archive In...*,
  *Restore* (Restore trashed file)
* Add accelerators `Control+R` for reset, `Control+S` for select first
  (source) pane and `Control+.` for untoggle text mode.
* Only the bookmarks plugins can toggle "include in toplevel" now.
* Other smaller changes (Refuse invalid Application objects from the
  cache)

This release is localized in: Swedish (100%), Italian (93%)

kupfer version c9.1
-------------------

* User interface consistency and behaviour improvements. UI is simpler and
  better.
* Other improvements.

This release is localized in: Swedish (100%), Italian (60%)

kupfer version c9
-----------------

The "c9" release

* Search and browse perform better
* The interface is now modal. In command mode we can bind special keys to
  new functions. Type period `.` to enter free-text mode (just like in QS).
* Pressing kupfer's keybinding again will hide the window.
* Other smaller improvements

This release is localized in: Swedish (100%), Italian (60%)

kupfer version c8
-----------------

* Make the use of the indirect object pane much more fluid
* Apply interface polish (proper english capitalization of actions and
  other objects, other changes)
* Add `Copy To...` action
* Try `xdg-terminal` first in *Open Terminal Here* (non-Gnome users can
  either install `xdg-terminal` or symlink it to their terminal program)
* Allow unbinding the keybinding
* Fix a bug with tracker tags

[Please file bug reports and feature requests.][lp]. Read the files in
`Documentation/` and see how you can add new plugins with object and 
application knowledge to kupfer.

This release is localized in: Swedish (100%), Italian (60%)

[lp]: http://launchpad.net/kupfer

kupfer version c7
-----------------

The "choice" release

This is a followup with some small changes after the c6 release, which
introduced lots of major changes, including a preferences window and
"application content."

* Allow wnck to be optional. Kupfer needs wnck to do application matching
  and focusing of already running applications, but can now run without it if
  wnck is not available. Window List plugin also needs wnck
* Rhythmbox plugin should not crash even if library is not found, now kupfer
  can run even if rhythmbox's files are not there.
* Applications will match names as well as the executables, so that "gedit"
  matches Text Editor regardless of what the displayed localized name is.


[Please file bug reports and feature requests.][lp]. Read the files in
`Documentation/` and see how you can add new plugins with object and 
application knowledge to kupfer.

This release is localized in: Swedish (100%), Italian (60%)

[lp]: http://launchpad.net/kupfer

kupfer version c6
-----------------

The "Sisyphus incremental improvements" release

* Preferences window
  
  * Allows setting keybinding on the fly
  * List and enable/disable plugins and set plugin options

* Everything was improved slightly, but steadily
* Understands more applications, provides more files and objects,
  and actions with **new plugins:** *Rhythmbox, Abiword, Clipboards, Dictionary,
  Favorites, Selected Text, Wikipedia*
* Connect applications with their related object sources and make it their
  content, such as Rhythmbox music for the Rhythmbox application.

  * Applications contain their recently used documents, if
    available.
  * Firefox and Epiphany bookmarks are identified with each application

* Miscellaneous improvements:

  * Kupfer object icon ("blue box")
  * *Some* default application associations are installed (others
    are learned by launching applications).
  * Experimental UI with two-line title+description in browse mode
  * Thumbnails for files and albums in browse mode
  * Allow sending files and queries to kupfer from the commandline
    using `kupfer 'query'` or `kupfer docs/file.pdf`.
  * Even more plugins listen to change callbacks or filesystem monitors
    to be up to date to the instant.
  * Do not display nonexisting files as results
  * Fine-tune how sources are loaded and refreshed on load

This release deserves lots of testing. [File bug reports and feature
requests.][bug] Read the files in `Documentation/` and see how you can add
new plugins with object and application knowledge to kupfer.

This release is localized in: Swedish (100%), Italian (60%)

Future: part 2 of beautification is refactoring of the interface, so
that the UI can be modularized and exchanged in plugins.

[bug]: http://launchpad.net/kupfer

kupfer version c5
-----------------

The "Beauty from the inside, part 1" release

* Big refactorings of the whole data model

  * Move all of the data model to kupfer.data
  * Allow actions with indirect objects "threepane kupfer" (with
    means to configure which objects to use for an action etc)
  * Uses unicode internally, instead of UTF-8-encoded strings

* Some new actions using new possibilities (Open with any, Move file
  to new location, Add/Remove tracker tags) but more is possible.
* Basic manual page included
* Fileactions plugin includes unpack archive/create archive
* Ship extra and demonstration plugins in contrib/ and interals
  documentation in Documentation/
* Change learning algorithm to recognize an item's type as well
  (so that two objects named "project" can be ranked differently)
* Small fixes (alphabethic sorting for applications, sources, check
  if objects still exist after an action, ``rank_adjust`` default actions
  slightly)

This release deserves lots of testing. File bug reports and feature
requests. Read the files in Documentation/ and see how you can add
new plugins with object and application knowledge to kupfer.

This release is localized in: Swedish (100%), Italian (80%)

Future: part 2 of beautification is refactoring of the interface, so
that the UI can be exchanged. And preferences will hopefully be implemented

.. -*- encoding: UTF-8 -*-
.. vim: tw=76 ft=rst
