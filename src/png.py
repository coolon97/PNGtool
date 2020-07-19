import zlib


class Buffer:
    def __init__(self, _bytes=None):
        if _bytes is None:
            self.set_bytes(b'')
        else:
            self.set_bytes(_bytes)

    def read(self, bytes_num=None):
        if bytes_num is None:
            _ = self.__bytes[self.__cursor:]
            self.begin()
            return _
        _ = self.__bytes[self.__cursor:self.__cursor + bytes_num]
        self.__cursor += bytes_num
        return _

    def write(self, _bytes, bytes_num=None, byte_order='big'):
        if bytes_num is None:
            self.__bytes += _bytes
        else:
            self.__bytes += _bytes.to_bytes(bytes_num, byte_order)

    def get_size(self):
        return len(self.__bytes)

    def set_bytes(self, _bytes):
        self.__bytes = _bytes
        self.__cursor = 0

    def begin(self):
        self.__cursor = 0


class Png:
    def __init__(self, filepath):
        print("file " + filepath + " Loading...")

        self.ihdr = {
            'size': (13).to_bytes(4, 'big'),
            'name': b'IHDR',
            'width': None,
            'height': None,
            'depth': None,
            'color': None,
            'comp': None,
            'fil': None,
            'interlace': None
        }

        self.read(filepath)

    def read(self, filepath):
        _bytes = b''
        with open(filepath, 'rb') as f:
            _bytes = f.read()
            f.close()
        self.IMG = self.__read_img(Buffer(_bytes))

    def __read_img(self, buf):
        if buf.read(8) != b'\x89PNG\r\n\x1a\n':
            print("This file is not PNG format.")

        buf.read(4)
        if buf.read(4) != b'IHDR':
            print("Invalid: Not found IHDR chunk")

        self.ihdr['width'] = buf.read(4)
        self.ihdr['height'] = buf.read(4)
        self.ihdr['depth'] = buf.read(1)
        self.ihdr['color'] = buf.read(1)
        self.ihdr['comp'] = buf.read(1)
        self.ihdr['fil'] = buf.read(1)
        self.ihdr['interlace'] = buf.read(1)

        ihdr_bytes = b''.join(
            [value for (key, value) in self.ihdr.items()][1:])
        self.ihdr['crc'] = buf.read(4)

        for (key, value) in self.ihdr.items():
            if key != 'name':
                self.ihdr[key] = int.from_bytes(value, 'big')

        if self.ihdr['comp'] != 0:
            print("Invalid: Unknown compression method")
        if self.ihdr['fil'] < 0 or self.ihdr['fil'] > 4:
            print("Invalid: Unknown filter method")
        if zlib.crc32(ihdr_bytes) != self.ihdr['crc']:
            print("Invalid: CRC dose not match")

        compressed_img = b''
        is_chunk = True
        while (is_chunk):
            size = int.from_bytes(buf.read(4), 'big')
            name = buf.read(4)
            #print("chunk: " + name.decode('ascii'))

            if name == b'IEND':
                is_chunk = False
            elif name == b'IDAT':
                img = buf.read(size)
                if int.from_bytes(buf.read(4), 'big') != zlib.crc32(name + img):
                    print('Invalid: CRC dose not match')
                compressed_img += img
            else:
                buf.read(size + 4)

        decompressed_img = zlib.decompress(compressed_img)

        bytes_perpixel = 1
        if self.ihdr['color'] == 0:
            pass
        elif self.ihdr['color'] == 2:
            bytes_perpixel = 3
        elif self.ihdr['color'] == 3:
            pass
        elif self.ihdr['color'] == 4:
            bytes_perpixel = 2
        elif self.ihdr['color'] == 6:
            bytes_perpixel = 4
        else:
            print("Invalid: Unknown color type.")

        return self.__reconstruction(decompressed_img, bytes_perpixel)

    def __reconstruction(self, decompressed_img, bytes_perpixel):
        row_size = int(bytes_perpixel * self.ihdr['width'] + 1)
        prev_row = bytearray(b'\x00' * row_size)
        decompressed_img = bytearray(decompressed_img)

        for h in range(self.ihdr['height']):
            offset = h*row_size
            row = decompressed_img[offset:offset+row_size]
            _filter = row[0]
            current_scan = row[1:]
            prev_scan = prev_row[1:]

            if _filter == 1:
                for i in range(bytes_perpixel, len(current_scan)):
                    current_scan[i] = (
                        current_scan[i-bytes_perpixel] + current_scan[i]) % 256
            elif _filter == 2:
                for i in range(0, len(current_scan)):
                    current_scan[i] = (prev_scan[i] + current_scan[i]) % 256
            elif _filter == 3:
                for i in range(bytes_perpixel):
                    current_scan[i] = (
                        current_scan[i] + int(prev_scan[i] / 2)) % 256
                for i in range(bytes_perpixel, len(current_scan)):
                    _ = int(
                        (current_scan[i-bytes_perpixel] + prev_scan[i]) / 2)
                    current_scan[i] = (_ + current_scan[i]) % 256
            elif _filter == 4:
                a, b, c, Pr = 0, 0, 0, 0
                for i in range(bytes_perpixel):
                    b = prev_scan[i]
                    pa = abs(b - c)
                    pb = abs(a - c)
                    pc = abs(a + b - 2 * c)
                    if pa <= pb and pa <= pc:
                        Pr = a
                    elif pb <= pc:
                        Pr = b
                    else:
                        Pr = c
                    current_scan[i] = (current_scan[i] + Pr) % 256
                for i in range(bytes_perpixel, len(current_scan)):
                    a = current_scan[i - bytes_perpixel]
                    c = prev_scan[i - bytes_perpixel]
                    b = prev_scan[i]
                    pa = abs(b - c)
                    pb = abs(a - c)
                    pc = abs(a + b - 2 * c)
                    if pa <= pb and pa <= pc:
                        Pr = a
                    elif pb <= pc:
                        Pr = b
                    else:
                        Pr = c
                    current_scan[i] = (current_scan[i] + Pr) % 256

            decompressed_img[offset:offset + row_size] = _filter.to_bytes(
                1, 'big') + current_scan
            prev_row = _filter.to_bytes(1, 'big') + current_scan

        return decompressed_img

    def write(self, filepath):
        raw = b''
        raw += b'\x89PNG\r\n\x1a\n'
        raw += (self.ihdr['size']).to_bytes(4, 'big')
        raw += (self.ihdr['name'])
        raw += (self.ihdr['width']).to_bytes(4, 'big')
        raw += (self.ihdr['height']).to_bytes(4, 'big')
        raw += (self.ihdr['depth']).to_bytes(1, 'big')
        raw += (self.ihdr['color']).to_bytes(1, 'big')
        raw += (self.ihdr['comp']).to_bytes(1, 'big')
        raw += (self.ihdr['fil']).to_bytes(1, 'big')
        raw += (self.ihdr['interlace']).to_bytes(1, 'big')
        raw += (self.ihdr['crc']).to_bytes(4, 'big')

        row_size = int(len(self.IMG) / self.ihdr['height'])
        for i in range(self.ihdr['height']):
            self.IMG[i*row_size] = 0
        compressed_img = zlib.compress(self.IMG)
        raw += len(compressed_img).to_bytes(4, 'big')
        raw += b'IDAT'
        raw += compressed_img
        raw += zlib.crc32(b'IDAT' + compressed_img).to_bytes(4, 'big')

        raw += (0).to_bytes(4, 'big')
        raw += b'IEND'
        raw += zlib.crc32(b'IEND').to_bytes(4, 'big')

        with open(filepath, 'wb') as f:
            f.write(raw)
            f.close()
    
    def write_binary(self, img, width, height):
        import numpy as np
        ihdr = {
            'size': (13).to_bytes(4, 'big'),
            'name': b'IHDR',
            'width': width,
            'height': height,
            'depth': 8,
            'color': 2,
            'comp': 0,
            'fil': 0,
            'interlace': 0
        }

        img = np.ravel(img)

        raw = b''
        raw += b'\x89PNG\r\n\x1a\n'
        raw += (ihdr['size']).to_bytes(4, 'big')
        head = (ihdr['name']) + (ihdr['width']).to_bytes(4, 'big') + (ihdr['height']).to_bytes(4, 'big')\
                + (ihdr['depth']).to_bytes(1, 'big') + (ihdr['color']).to_bytes(1, 'big') + (ihdr['comp']).to_bytes(1, 'big')\
                + (ihdr['interlace']).to_bytes(1, 'big') + (ihdr['interlace']).to_bytes(1, 'big')
        raw += head
        raw += zlib.crc32(head).to_bytes(4, 'big')

        row_size = int(len(img) / self.ihdr['height'])
        for i in range(self.ihdr['height']):
            img[i*row_size] = 0
        compressed_img = zlib.compress(img)
        raw += len(compressed_img).to_bytes(4, 'big')
        raw += b'IDAT'
        raw += compressed_img
        raw += zlib.crc32(b'IDAT' + compressed_img).to_bytes(4, 'big')

        raw += (0).to_bytes(4, 'big')
        raw += b'IEND'
        raw += zlib.crc32(b'IEND').to_bytes(4, 'big')

        with open("png_b.png", 'wb') as f:
            f.write(raw)
            f.close()

    def info(self):
        for (key, value) in self.ihdr.items():
            print(str(key) + ": " + str(value))

    def size(self):
        return (self.ihdr["width"], self.ihdr["height"])

    def get_rgb(self):
        pass

    def get_rgba(self):
        pass

    def decompress(self, data):
        pass


if __name__ == "__main__":
    p = Png("../Assets/lenna.png")
    p.write("../Assets/out.png")
