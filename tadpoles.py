import time
from requests import session
from tpcredentials import email, password, directory
import hashlib
import sys
import os


payload = { 'email': email, 'password': password }
url = 'https://www.tadpoles.com/auth/login'
path = directory

def main():
    if not os.path.exists(path):
        print(path, 'does not exist on your filesystem')
        sys.exit(1)
    elif not os.path.isdir(path):
        print(path, 'is not a folder on your filesystem')
        sys.exit(1)
    else:
        downloadimgs()

def downloadimgs():
    with session() as c:
        c.post(url, data=payload)
        c.get('https://www.tadpoles.com/parents?app=parent&')
        jsondata = c.get('https://www.tadpoles.com/remote/v1/events?direction=range&earliest_event_time=1&latest_event_time=99999999999&num_events=300&client=dashboard').json()
        for img in jsondata['events']:
            for imgkey in img['attachments']:
                link = 'https://www.tadpoles.com/remote/v1/attachment?key=' + imgkey
                result = c.get(link, stream=True)
                if result.status_code == 200:
                    image = result.raw.read()
                    filename = hashlib.md5(imgkey.encode('utf-8')).hexdigest() + '.jpg'
                    open(path + filename, 'wb').write(image)
                    print("writing image to file {}".format(imgkey,filename))


def uploaddropbox():
    return

if __name__== "__main__":
  main()
