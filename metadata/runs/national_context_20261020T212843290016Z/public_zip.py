"""Read selected members of a public ZIP through validated HTTP ranges."""
import io
from pathlib import Path
import re
import zipfile

class RangeReader(io.RawIOBase):
    def __init__(self,size,fetch):
        self.size=size;self.fetch=fetch;self.position=0
    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.position
    def seek(self,offset,whence=0):
        position=offset if whence==0 else self.position+offset if whence==1 else self.size+offset
        if position<0:raise ValueError('Negative seek')
        self.position=position;return position
    def read(self,size=-1):
        end=self.size if size<0 else min(self.size,self.position+size)
        if end<=self.position:return b''
        content=self.fetch(self.position,end-1)
        if len(content)!=end-self.position:raise IOError('Incomplete ZIP range')
        self.position=end;return content


def download_members(url,destination,prefix):
    """Preserve exact member bytes; ZIP verifies decompression CRCs on read."""
    import requests
    session=requests.Session();session.headers['User-Agent']='HeritageFloodResearch/0.1 (public-data research)'
    response=session.get(url,headers={'Range':'bytes=0-0'},timeout=60);response.raise_for_status()
    content_range=response.headers.get('Content-Range','');match=re.fullmatch(r'bytes 0-0/(\d+)',content_range)
    if response.status_code!=206 or not match:raise IOError('Server must support exact HTTP ranges')
    size=int(match.group(1));identity={k:response.headers.get(k) for k in ['ETag','Last-Modified']}
    def fetch(start,end):
        response=session.get(url,headers={'Range':f'bytes={start}-{end}'},timeout=120);response.raise_for_status()
        if response.status_code!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{size}':raise IOError('Invalid HTTP range response')
        if any(value and response.headers.get(key)!=value for key,value in identity.items()):raise IOError('Source ZIP changed during download')
        return response.content
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True);files=[]
    with zipfile.ZipFile(RangeReader(size,fetch)) as archive:
        for member in archive.infolist():
            if not member.filename.startswith(prefix):continue
            path=destination/Path(member.filename).name
            # Read again on resume to ensure CRC and source identity apply to this run.
            content=archive.read(member)
            path.write_bytes(content);files.append(path.name)
            print('Retained ZIP member',path.name,len(content),flush=True)
    return {'url':url,'archive_size_bytes':size,'http_identity':identity,'members':files}
