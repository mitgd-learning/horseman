from io import BytesIO
from multidict import MultiDict
from multifruits import Parser, extract_filename, parse_content_disposition


class Multipart:
    """Responsible of the parsing of multipart encoded `request.body`.
    """

    __slots__ = (
        'form',
        'files',
        '_parser',
        '_current',
        '_current_headers',
        '_current_params')

    def __init__(self, content_type: str):
        self._parser = Parser(self, content_type.encode())
        self.form = MultiDict()
        self.files = MultiDict()

    def feed_data(self, data: bytes):
        self._parser.feed_data(data)

    def on_part_begin(self):
        self._current_headers = {}

    def on_header(self, field: bytes, value: bytes):
        self._current_headers[field] = value

    def on_headers_complete(self):
        disposition_type, params = parse_content_disposition(
            self._current_headers.get(b'Content-Disposition'))
        if not disposition_type:
            raise ValueError('Content-Disposition is missing.')

        self._current_params = params
        if b'Content-Type' in self._current_headers:
            self._current = BytesIO()
            self._current.filename = extract_filename(params)
            self._current.content_type = self._current_headers[b'Content-Type']
            self._current.params = params
        else:
            self._current = ''

    def on_data(self, data: bytes):
        if b'Content-Type' in self._current_headers:
            self._current.write(data)
        else:
            self._current += data.decode()

    def on_part_complete(self):
        name = self._current_params.get(b'name', b'').decode()
        if b'Content-Type' in self._current_headers:
            self._current.seek(0)
            self.files.add(name, self._current)
        else:
            self.form.add(name, self._current)
        self._current = None
