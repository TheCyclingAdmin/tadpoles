import time
from requests import session
from tpcredentials import email, password, directory
import hashlib
import dropbox

payload = { 'email': email, 'password': password }
url = 'https://www.tadpoles.com/auth/login'
filedir = directory

def main():
    getimagelinks()

def getimagelinks():
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
                    filename = hashlib.md5(imgkey).hexdigest()
                    open( filedir + filename + '.jpg', 'wb').write(image)
                    print("writing image to file {}".format(imgkey,filename))


def uploaddropbox():

    client = dropbox.client.DropboxClient( < auth_token >)
    print('linked account: ', client.account_info())

    f = open('working-draft.txt', 'rb')
    response = client.put_file('/magnum-opus.txt', f)
    print('uploaded: ', response)

    folder_metadata = client.metadata('/')
    print('metadata: ', folder_metadata)

    f, metadata = client.get_file_and_metadata('/magnum-opus.txt')
    out = open('magnum-opus.txt', 'wb')
    out.write(f.read())
    out.close()
    print(metadata)

if __name__== "__main__":
  main()
