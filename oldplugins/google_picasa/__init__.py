# -*- coding: UTF-8 -*-
__kupfer_name__ = _("Google Picasa")
__kupfer_sources__ = ("PicasaUsersSource", )
__kupfer_actions__ = ('UploadFileToPicasa', 'UploadDirToPicasa')
__description__ = _("Show albums and upload files to Picasa")
__version__ = "2010-04-06"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import os.path
import time

import gdata.service
import gdata.photos.service

from kupfer.objects import Action, FileLeaf, TextLeaf
from kupfer.objects import UrlLeaf, Source
from kupfer.obj.special import PleaseConfigureLeaf, InvalidCredentialsLeaf
from kupfer import plugin_support, pretty, icons
from kupfer.ui.progress_dialog import ProgressDialogController
from kupfer import kupferstring
from kupfer import utils
from kupfer import task

plugin_support.check_keyring_support()

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        'key': 'userpass',
        'label': '',
        'type': plugin_support.UserNamePassword,
        'value': "",
    },
    {
        'key': 'showusers',
        'label': _('Users to show: (,-separated)'),
        'type': str,
        'value': '',
    },
    {
        'key': 'loadicons',
        'label': _('Load user and album icons'),
        'type': bool,
        'value': True,
    },
)


ALBUM_URL = '/data/feed/api/user/%s/albumid/%s'
USER_URL = 'http://picasaweb.google.com/%(user)s'


def is_plugin_configured():
    upass = __kupfer_settings__['userpass']
    return bool(upass and upass.username and upass.password)


def valid_file(filepath):
    ''' check is file supported by picasa '''
    extension = os.path.splitext(filepath)[1].lower()
    return extension in ('.jpg', '.jpeg', '.png', '.gif')


class UploadTask(task.ThreadTask):
    """ Uploading files to picasa """

    def __init__(self):
        task.ThreadTask.__init__(self)
        self._files_to_upload = []
        self._files_albums_count = 0

    def add_files_to_existing_album(self, files, album_id):
        ''' upload files to existing album.
        @files: list of local files (full path)
        @album_id: picasa album id
        '''
        self._files_to_upload.append((files, album_id, None))
        self._files_albums_count += len(files)

    def add_files_to_new_album(self, files, album_name):
        ''' create new album and upload files.
        @files: list of local files (full path)
        @album_name: new album name 
        '''
        self._files_to_upload.append((files, None, album_name))
        self._files_albums_count += len(files) + 1

    def thread_do(self):
        gd_client = picasa_login()
        if not gd_client:
            return
        progress_dialog = ProgressDialogController(
                _("Uploading Pictures"),
                _("Uploading pictures to Picasa Web Album"),
                max_value=self._files_albums_count)
        progress_dialog.show()
        try:
            upass = __kupfer_settings__['userpass']
            progress = 0
            for files, album_id, album_name in self._files_to_upload:
                # create album
                if album_id is None:
                    progress_dialog.update(progress, _("Creating album:"),
                            album_name)
                    album = gd_client.InsertAlbum(title=album_name,
                            summary=_('Album created by Kupfer'))
                    album_id = album.gphoto_id.text
                    progress += 1
                # send files
                album_url = ALBUM_URL % (upass.username, album_id)
                for filename in files:
                    pretty.print_debug(__name__, 'upload: sending', filename)
                    progress_dialog.update(progress, _('File:'),
                            utils.get_display_path_for_bytestring(filename))
                    if progress_dialog.aborted:
                        pretty.print_debug(__name__, 'upload: abort')
                        break
                    # send file
                    gd_client.InsertPhotoSimple(album_url,
                            os.path.basename(filename), '', filename)
                    pretty.print_debug(__name__, 'upload: file sended', filename)
                    progress += 1

        except (gdata.service.Error, gdata.photos.service.GooglePhotosException) as \
                err:
            pretty.print_error(__name__, 'upload error', err)

        finally:
            progress_dialog.hide()

    def thread_finish(self):
        pass


def picasa_login():
    if not is_plugin_configured():
        return None
    gd_client = None
    try:
        upass = __kupfer_settings__['userpass']
        gd_client = gdata.photos.service.PhotosService()
        gd_client.email = upass.username
        gd_client.password = upass.password
        gd_client.source = 'kupfer-google_picasa'
        gd_client.ProgrammaticLogin()
    except (gdata.service.BadAuthentication, gdata.service.CaptchaRequired) as err:
        pretty.print_error(__name__, 'picasa_login', 'authentication error',
                err)
        gd_client = None
    return gd_client


def get_thumb(gd_client, thumb_url):
    ''' Load thumb from web '''
    thumb = None
    if thumb_url:
        thumb_media = gd_client.GetMedia(thumb_url)
        if thumb_media:
            thumb = thumb_media.file_handle.read()
    return thumb


def get_user_leaf(gd_client, user_name):
    ''' Create PicasaUser obj for given @user_name. '''
    leaf = None
    try:
        user_info = gd_client.GetContacts(user_name)
    except gdata.photos.service.GooglePhotosException as err:
        pretty.print_info(__name__, 'get_uers_leaf', err)
    else:
        thumb = None
        if __kupfer_settings__['loadicons']:
            thumb = get_thumb(gd_client, user_info.thumbnail.text)
        user_url = USER_URL % dict(user=user_info.user.text)
        leaf = PicasaUser(user_url, kupferstring.tounicode(user_info.nickname.text),
                thumb)
    return leaf


class PicasaDataCache():
    data = []

    @classmethod
    def get_albums(cls, force=False):
        ''' Load user albums, and albums users defined in 'showusers' setting. '''
        pretty.print_debug(__name__, 'get_albums', str(force))
        if not force:
            return cls.data
        start_time = time.time()
        gd_client = picasa_login()
        if not gd_client:
            return [InvalidCredentialsLeaf(__name__, __kupfer_name__)]

        pusers = []
        try:
            user = __kupfer_settings__['userpass'].username
            show_users = (__kupfer_settings__['showusers'] or '')
            user_names = [U.strip() for U in show_users.split(',') if U.strip()]

            if user not in user_names:
                user_names.append(user)

            for user_name in user_names:
                pretty.print_debug(__name__, 'get_albums: get album', user_name)
                # get user info
                picasa_user_leaf = get_user_leaf(gd_client, user_name)
                if picasa_user_leaf is None:
                    continue
                picasa_user_leaf.my_albums = (user_name == user) # mark my albums
                # get albums
                user_albums = []
                for album in gd_client.GetUserFeed(user=user_name).entry:
                    # get album thumbnail:
                    thumb = None
                    if album.media.thumbnail and __kupfer_settings__['loadicons']:
                        thumb = get_thumb(gd_client, album.media.thumbnail[0].url)
                    name = kupferstring.tounicode(album.title.text)
                    album = PicasaAlbum(album.GetAlternateLink().href,
                            name, album.numphotos.text,
                            album.gphoto_id.text, thumb,
                            kupferstring.tounicode(user_name))
                    user_albums.append(album)
                picasa_user_leaf.update_albums(user_albums)
                pusers.append(picasa_user_leaf)
        except gdata.service.Error as err:
            pretty.print_error(__name__, 'get_albums', err)
        pretty.print_debug(__name__, 'get_albums finished', 'loaded: ', len(pusers),
                str(time.time()-start_time))
        cls.data = pusers
        return pusers


def _get_valid_files_in_dir(dir_path):
    ''' get all files acceptable by picasa in given directory '''
    files = [os.path.join(dir_path, filename)
            for filename  in os.listdir(dir_path)
            if valid_file(filename)]
    return files


class PicasaUser(UrlLeaf):
    ''' Leaf represent user from Picasa '''
    def __init__(self, url, name, thumb=None, albums=None):
        UrlLeaf.__init__(self, url, name)
        # list of user albums [PicasaAlbum]
        self.update_albums(albums)
        self.thumb = thumb
        self.my_albums = False

    def update_albums(self, albums):
        self.albums = albums or []
        albums_count = len(self.albums)
        self.description = ngettext("One album", "%(num)d albums",
            albums_count) % {"num": albums_count}

    def has_content(self):
        return bool(self.albums)

    def content_source(self, alternate=False):
        return PicasaAlbumSource(self)

    def get_thumbnail(self, width, height):
        if self.thumb:
            return icons.get_pixbuf_from_data(self.thumb, width, height)
        return UrlLeaf.get_thumbnail(self, width, height)

    def get_gicon(self):
        return icons.ComposedIconSmall("stock_person", "picasa")

    def get_description(self):
        return self.description


class PicasaAlbum(UrlLeaf):
    ''' Leaf represent single album in Picasa '''
    def __init__(self, url, name, pict_count, album_id, thumb, user):
        UrlLeaf.__init__(self, url, name)
        self.album_id = album_id
        self.thumb = thumb
        photos_info = ngettext("one photo", "%(num)s photos",
                int(pict_count)) % {"num": pict_count}
        self.description = ': '.join((user, photos_info))

    def get_description(self):
        return self.description

    def get_thumbnail(self, width, height):
        if self.thumb:
            return icons.get_pixbuf_from_data(self.thumb, width, height)
        return UrlLeaf.get_thumbnail(self, width, height)

    def get_gicon(self):
        return icons.ComposedIconSmall(self.get_icon_name(), "picasa")


class UploadFileToPicasa(Action):
    ''' upload selected files or files from selected dirs into existing
        album or new album (by enter new name) '''
    def __init__(self):
        Action.__init__(self, _('Upload to Picasa Album...'))

    def activate(self, obj, iobj):
        return self.activate_multiple((obj, ), (iobj, ))

    def activate_multiple(self, objects, iobjects):
        utask = UploadTask()
        files = []
        for obj in objects:
            if obj.is_dir():
                files.extend(_get_valid_files_in_dir(obj.object))
            else:
                files.append(obj.object)
        for iobj in iobjects:
            if isinstance(iobj, PicasaAlbum):
                utask.add_files_to_existing_album(files, iobj.album_id)
            else:
                utask.add_files_to_new_album(files, iobj.object)
        return utask

    def is_async(self):
        return True

    def get_icon_name(self):
        return "document-save"

    def item_types(self):
        yield FileLeaf

    def valid_for_item(self, item):
        return (valid_file(item.object) or item.is_dir()) \
                and is_plugin_configured()

    def requires_object(self):
        return True

    def object_types(self):
        yield PicasaAlbum
        yield TextLeaf

    def object_source(self, for_item=None):
        return PicasaPrivAlbumsSource()

    def get_description(self):
        return _("Upload files to Picasa album")


class UploadDirToPicasa(Action):
    ''' Upload whole directories as new albums '''
    def __init__(self):
        Action.__init__(self, _('Upload to Picasa as New Album'))

    def activate(self, obj):
        return self.activate_multiple((obj, ))

    def activate_multiple(self, objects):
        utask = UploadTask()
        for obj in objects:
            dir_path = obj.object
            files_to_upload = _get_valid_files_in_dir(dir_path)
            if files_to_upload:
                album_name = os.path.basename(dir_path)
                utask.add_files_to_new_album(files_to_upload, album_name)
        return utask

    def is_async(self):
        return True

    def get_icon_name(self):
        return "document-save"

    def item_types(self):
        yield FileLeaf

    def valid_for_item(self, item):
        return item.is_dir() and is_plugin_configured()

    def get_description(self):
        return _("Create album from selected local directory")


class PicasaPrivAlbumsSource(Source):
    def __init__(self, name=_("Picasa Albums")):
        Source.__init__(self, name)

    def get_items(self):
        if is_plugin_configured():
            for user in PicasaDataCache.get_albums():
                if user.my_albums:
                    return user.albums
        return []

    def should_sort_lexically(self):
        return True

    def provides(self):
        yield PicasaAlbum

    def get_icon_name(self):
        return "picasa"


class PicasaUsersSource(Source):
    source_user_reloadable = True

    def __init__(self, name=_("Picasa Albums")):
        Source.__init__(self, name)
        self._version = 2

    def initialize(self):
        # fill loader cache by source cache
        PicasaDataCache.data = self.cached_items or []
        __kupfer_settings__.connect("plugin-setting-changed", self._changed)

    def _changed(self, settings, key, value):
        if key == "userpass":
            PicasaDataCache.data = []
            self.mark_for_update()

    def get_items(self):
        if is_plugin_configured():
            return PicasaDataCache.get_albums()
        return [PleaseConfigureLeaf(__name__, __kupfer_name__)]

    def get_items_forced(self):
        if is_plugin_configured():
            return PicasaDataCache.get_albums(True)
        return [PleaseConfigureLeaf(__name__, __kupfer_name__)]

    def should_sort_lexically(self):
        return True

    def provides(self):
        yield PicasaUser
        yield PleaseConfigureLeaf

    def get_description(self):
        return _("User albums in Picasa")

    def get_icon_name(self):
        return "picasa"


class PicasaAlbumSource(Source):
    """ Source return albums for given user"""
    def __init__(self, picasa_user, name=_("Albums")):
        Source.__init__(self, name)
        self.picasa_user = picasa_user

    def get_items(self):
        return self.picasa_user.albums

    def should_sort_lexically(self):
        return True

    def provides(self):
        yield PicasaAlbum

    def has_parent(self):
        return True

    def get_parent(self):
        return self.picasa_user

    def get_icon_name(self):
        return "picasa"
