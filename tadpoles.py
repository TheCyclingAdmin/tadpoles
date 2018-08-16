from requests import session
from tpcredentials import email, password, dbxtoken, dbxfolder, localdir
import hashlib
import datetime
import os
import six
import sys
import time
import unicodedata
from contextlib import contextmanager
import dropbox

auth = { 'email': email, 'password': password }
baseurl = 'https://www.tadpoles.com/'
dbx = dropbox.Dropbox(dbxtoken)
folder = dbxfolder
rootdir = os.path.expanduser(localdir)
eventcount = '&num_events=300'
firsteventtime = '&earliest_event_time=1'
lasteventtime = '&latest_event_time=99999999999'

def main():
    #Small sanity checks
    checkfolders()

    #Login and download latest images
    downloadimgs()

    dbx = dropbox.Dropbox(dbxtoken)

    for dn, dirs, files in os.walk(rootdir):
        subfolder = dn[len(rootdir):].strip(os.path.sep)
        listing = list_folder(dbx, folder, subfolder)
        print('Descending into', subfolder, '...')

        # First do all the files.
        for name in files:
            fullname = os.path.join(dn, name)
            if not isinstance(name, six.text_type):
                name = name.decode('utf-8')
            nname = unicodedata.normalize('NFC', name)
            if name.startswith('.'):
                print('Skipping dot file:', name)
            elif name.startswith('@') or name.endswith('~'):
                print('Skipping temporary file:', name)
            elif name.endswith('.pyc') or name.endswith('.pyo'):
                print('Skipping generated file:', name)
            elif nname in listing:
                md = listing[nname]
                mtime = os.path.getmtime(fullname)
                mtime_dt = datetime.datetime(*time.gmtime(mtime)[:6])
                size = os.path.getsize(fullname)
                if (isinstance(md, dropbox.files.FileMetadata) and
                        mtime_dt == md.client_modified and size == md.size):
                    print(name, 'is already synced [stats match]')
                else:
                    print(name, 'exists with different stats, downloading')
                    res = download(dbx, folder, subfolder, name)
                    with open(fullname) as f:
                        data = f.read()
                    if res == data:
                        print(name, 'is already synced [content match]')
                    else:
                        print(name, 'has changed since last sync')
                        upload(dbx, fullname, folder, subfolder, name, overwrite=True)
            else:
                upload(dbx, fullname, folder, subfolder, name)

        # Then choose which subdirectories to traverse.
        keep = []
        for name in dirs:
            if name.startswith('.'):
                print('Skipping dot directory:', name)
            elif name.startswith('@') or name.endswith('~'):
                print('Skipping temporary directory:', name)
            elif name == '__pycache__':
                print('Skipping generated directory:', name)
                print('Descend into %s' % name)
                print('Keeping directory:', name)
                keep.append(name)
            else:
                print('OK, skipping directory:', name)
        dirs[:] = keep


def list_folder( dbx, folder, subfolder ):
    """List a folder.
    Return a dict mapping unicode filenames to
    FileMetadata|FolderMetadata entries.
    """
    path = '/%s/%s' % (folder, subfolder.replace(os.path.sep, '/'))
    while '//' in path:
        path = path.replace('//', '/')
    path = path.rstrip('/')
    try:
        with stopwatch('list_folder'):
            res = dbx.files_list_folder(path)
    except dropbox.exceptions.ApiError as err:
        print('Folder listing failed for', path, '-- assumed empty:', err)
        return { }
    else:
        rv = { }
        for entry in res.entries:
            rv[entry.name] = entry
        return rv


def download( dbx, folder, subfolder, name ):
    """Download a file.
    Return the bytes of the file, or None if it doesn't exist.
    """
    path = '/%s/%s/%s' % (folder, subfolder.replace(os.path.sep, '/'), name)
    while '//' in path:
        path = path.replace('//', '/')
    with stopwatch('download'):
        try:
            md, res = dbx.files_download(path)
        except dropbox.exceptions.HttpError as err:
            print('*** HTTP error', err)
            return None
    data = res.content
    print(len(data), 'bytes; md:', md)
    return data


def upload( dbx, fullname, folder, subfolder, name, overwrite=False ):
    """Upload a file.
    Return the request response, or None in case of error.
    """
    path = '/%s/%s/%s' % (folder, subfolder.replace(os.path.sep, '/'), name)
    while '//' in path:
        path = path.replace('//', '/')
    mode = (dropbox.files.WriteMode.overwrite
            if overwrite
            else dropbox.files.WriteMode.add)
    mtime = os.path.getmtime(fullname)
    with open(fullname, 'rb') as f:
        data = f.read()
    with stopwatch('upload %d bytes' % len(data)):
        try:
            res = dbx.files_upload(
                data, path, mode,
                client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                mute=True)
        except dropbox.exceptions.ApiError as err:
            print('*** API error', err)
            return None
    print('uploaded as', res.name.encode('utf8'))
    return res


def downloadimgs():
    with session() as c:
        c.post(baseurl + 'auth/login', data=auth)
        c.get(baseurl + 'parents?app=parent&')
        jsondata = c.get(baseurl + 'remote/v1/events?direction=range&client=dashboard' + firsteventtime + lasteventtime + eventcount ).json()
        for img in jsondata['events']:
            for imgkey in img['attachments']:
                link = baseurl + 'remote/v1/attachment?key=' + imgkey
                result = c.get(link, stream=True)
                if result.status_code == 200:
                    content_type = result.headers['content-type']
                    if content_type == 'image/jpeg':
                        ext = '.jpg'
                    elif content_type == 'image/png':
                        ext = '.png'
                    elif content_type == 'video/mp4':
                        ext = '.mp4'
                    image = result.raw.read()
                    filename = hashlib.md5(imgkey.encode('utf-8')).hexdigest() + ext
                    if os.path.isfile(localdir + filename):
                        print("File {} already exists.".format(filename))
                    else:
                        print("writing image to file {}".format(filename))
                        open(localdir + filename, 'wb').write(image)

def checkfolders():
    print('Dropbox folder name:', folder)
    print('Local directory:', rootdir)
    if not os.path.exists(rootdir):
        print(rootdir, 'does not exist on your filesystem')
        sys.exit(1)
    elif not os.path.isdir(rootdir):
        print(rootdir, 'is not a folder on your filesystem')
        sys.exit(1)

@contextmanager
def stopwatch( message ):
    """Context manager to print how long a block of code took."""
    t0 = time.time()
    try:
        yield
    finally:
        t1 = time.time()
        print('Total elapsed time for %s: %.3f' % (message, t1 - t0))


if __name__ == "__main__":
    main()

