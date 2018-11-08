import mimetypes
import asyncio
import os
from urllib.parse import unquote

class HTTPHeader:
    def __init__(self):
        self.headers = {'method': '', 'path': ''}

    def parse_header(self, line):
        fileds = unquote(line, encoding='utf-8').split(' ')
        if str.upper(fileds[0]) == 'GET' or str.upper(fileds[0]) == 'HEAD':
            self.headers['method'] = str.upper(fileds[0])
            path = fileds[1]
            if(len(fileds) > 3):
                for i in range(2, len(fileds)-1):
                    path += ' ' + fileds[i]
            self.headers['path'] = path 


    def get(self, key):
        return self.headers.get(key)


async def dispatch(reader, writer):
    header = HTTPHeader()
    while True:
        data = await reader.readline()
        message = data.decode()
        header.parse_header(message)
        if data == b'\r\n':
            break
    # NOT SUPPORT method    
    if header.get('method') == '':
        writer.writelines([
            b'HTTP/1.0 405 Method Not Allowed\r\n',
            b'Content-Type:text/html; charset=utf-8\r\n',
            b'Connection: close\r\n',
            b'\r\n',
            b'<html><body>405 Method Not Allowed</body></html>\r\n',
            b'\r\n'
            ])
    # GET method    
    elif header.get('method') == 'GET':
        path = os.getcwd() + header.get('path')
        if os.path.exists(path): 
            if os.path.isdir(path):
                message = render_html(path, header.get('path'))
                
                writer.writelines([
                    b'HTTP/1.0 200 OK\r\n',
                    b'Content-Type:text/html; charset=utf-8\r\n',
                    b'Connection: close\r\n',
                    b'\r\n'
                    b'<html>',
                    str.encode(message),
                    b'</html>\r\n',
                    b'\r\n'
                    ])
        
            else:
                file = open(path, 'rb')
                filetype = mimetypes.guess_type(header.get('path'))[0]
                if filetype is None:
                    filetype = 'application/octet-stream'
                writer.writelines([
                    b'HTTP/1.0 200 OK\r\n',
                    b'Content-Type:',
                    str.encode(filetype),
                    b'\r\n',
                    b'Content-Length:',
                    str.encode(str(os.path.getsize(path))),
                    b'\r\n',
                    b'Connection: close\r\n',
                    b'\r\n',
                    file.read(),
                    b'\r\n'
                    ])
        
        else:
             writer.writelines([
                b'HTTP/1.0 404 Not Found\r\n',
                b'Content-Type:text/html; charset=utf-8\r\n',
                b'Connection: close\r\n',
                b'\r\n',
                b'<html><body>404 Not Found</body></html>\r\n',
                b'\r\n'
                ])
    # HEAD meathod         
    else:
        path = os.getcwd() + header.get('path')
        if os.path.exists(path): 
            if os.path.isdir(path):
                message = render_html(path, header.get('path'))
                writer.writelines([
                    b'HTTP/1.0 200 OK\r\n',
                    b'Content-Type:text/html; charset=utf-8\r\n',
                    b'Connection: close',
                    b'\r\n'
                    ])
        
            else:
                file = open(path, 'rb+')
                filetype = mimetypes.guess_type(header.get('path'))[0]
                if filetype is None:
                    filetype = 'application/octet-stream'
                writer.writelines([
                    b'HTTP/1.0 200 OK\r\n',
                    b'Content-Type:t\r\n',
                    str.encode(filetype),
                    b'; charset=utf-8\r\n',
                    b'Content-Length:',
                    str.encode(str(os.path.getsize(path))),
                    b'\r\n',
                    b'Connection: close\r\n',
                    b'\r\n'
                    ])
        
    await writer.drain()
    writer.close()

def render_html(path, current_path):
    message = ''
    message += '<head><title>' + 'Index of ' + path + '</title></head>\n'
    message += '<body bgcolor = "white">\n'
    message += '<h1>' + 'Index of ' + path + '</h1>\n'
    message += '<pre>\n'
    list = os.listdir(path)
    for element in list:
        if os.path.isdir(path + element):
            message += '<a href=\"' + current_path + element + '/\">' + element + '/</a><br>\n'
        else:
            message += '<a href=\"' + current_path + element + '\">' + element + '</a><br>\n'
    message += '</pre>\n'
    message += '</body>'
    return message 

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(dispatch, '127.0.0.1', 8080, loop=loop)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
