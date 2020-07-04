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
            print("chunk: " + name.decode('ascii'))

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
        img = [decompressed_img[h * row_size:h * row_size + row_size]
               for h in range(self.ihdr['height'])]
        img = [[c for c in img[h]] for h in range(self.ihdr['height'])]
        prevRowData = [0]*row_size
        for h in range(self.ihdr['height']):
            rowData = img[h]
            filterType = rowData[0]

            currentScanData = rowData[1:]
            prevScanData = prevRowData[1:]

            if filterType == 0:
                continue
            elif filterType == 1:
                for i in range(bytes_perpixel, len(currentScanData)):
                    currentScanData[i] = (
                        currentScanData[i-bytes_perpixel] + currentScanData[i]) % 256
            elif filterType == 2:
                for i in range(0, len(currentScanData)):
                    currentScanData[i] = (
                        prevScanData[i] + currentScanData[i]) % 256
            elif filterType == 3:
                for i in range(bytes_perpixel):
                    currentScanData[i] = (currentScanData[i] +
                                          int(prevScanData[i] / 2)) % 256
                for i in range(bytes_perpixel, len(currentScanData)):
                    _ = int(
                        (currentScanData[i-bytes_perpixel] + prevScanData[i]) / 2)
                    currentScanData[i] = (_ + currentScanData[i]) % 256
            elif filterType == 4:
                a, b, c, Pr = 0, 0, 0, 0
                for i in range(bytes_perpixel):
                    b = prevScanData[i]
                    pa = abs(b - c)
                    pb = abs(a - c)
                    pc = abs(a + b - 2 * c)
                    if pa <= pb and pa <= pc:
                        Pr = a
                    elif pb <= pc:
                        Pr = b
                    else:
                        Pr = c
                    currentScanData[i] = (currentScanData[i] + Pr) % 256
                for i in range(bytes_perpixel, len(currentScanData)):
                    a = currentScanData[i - bytes_perpixel]
                    c = prevScanData[i - bytes_perpixel]
                    b = prevScanData[i]
                    pa = abs(b - c)
                    pb = abs(a - c)
                    pc = abs(a + b - 2 * c)
                    if pa <= pb and pa <= pc:
                        Pr = a
                    elif pb <= pc:
                        Pr = b
                    else:
                        Pr = c
                    currentScanData[i] = (currentScanData[i] + Pr) % 256

            img[h][1:] = currentScanData
            prevRowData = rowData

        self.width = int(row_size/bytes_perpixel)
        self.height = len(img)
        return img

    def write(self, filepath):
        raw = Buffer()
        raw.write(b'\x89PNG\r\n\x1a\n')
        raw.write(self.ihdr['size'], 4)
        raw.write(self.ihdr['name'])
        raw.write(self.ihdr['width'], 4)
        raw.write(self.ihdr['height'], 4)
        raw.write(self.ihdr['depth'], 1)
        raw.write(self.ihdr['color'], 1)
        raw.write(self.ihdr['comp'], 1)
        raw.write(self.ihdr['fil'], 1)
        raw.write(self.ihdr['interlace'], 1)
        raw.write(self.ihdr['crc'], 4)

        for i in self.IMG:
            i[0] = 0
        img_raw = b''.join([(c).to_bytes(1, 'big')
                            for inner in self.IMG for c in inner])
        compressed_img = zlib.compress(img_raw)
        raw.write(len(compressed_img), 4)
        raw.write(b'IDAT')
        raw.write(compressed_img)
        raw.write(zlib.crc32(b'IDAT' + compressed_img), 4)

        raw.write(0, 4)
        raw.write(b'IEND')
        raw.write(zlib.crc32(b'IEND'), 4)

        with open(filepath, 'wb') as f:
            f.write(raw.read())
            f.close()

    def info(self):
        for (key, value) in self.ihdr.items():
            print(str(key) + ": " + str(value))

    def size(self):
        return (self.width, self.height)

    def get_rgb(self):
        pass

    def get_rgba(self):
        pass

    def decompress(self, data):
        pass


if __name__ == "__main__":
    p = Png("../Assets/test.png")
    # p = Png("test.png")
    p.write("../Assets/out.png")
