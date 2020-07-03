import zlib

PNG_HEAD = 8
IHDR_HEAD = 12
IHDR_WIDTH = 16
IHDR_HEGIHT = 20
IHDR_BITDEPTH = 24
IHDR_COLORTYPE = 25
IHDR_COMPTYPE = 26
IHDR_FILTYPE = 27
IHDR_INTERLACE = 28
IHDR_CRC = 29

CHUNK_STEP = 4


class PNG:
    def __init__(self, filepath=None):
        if filepath is not None:
            self.DATA = self.read(filepath)

    def read(self, filepath):
        print("file " + filepath + " Loading...")
        buf = b''
        with open(filepath, 'rb') as f:
            buf = f.read()
            f.close()
        self.readFromBinary(buf)

    def readFromBinary(self, buf):
        if buf[:PNG_HEAD] != b'\x89PNG\r\n\x1a\n':
            print("This file is not PNG format.")

        self.LENGTH = 13

        if buf[IHDR_HEAD:IHDR_WIDTH] != b'IHDR':
            print("Invalid: Not found IHDR chunk")

        self.WIDTH = int.from_bytes(buf[IHDR_WIDTH:IHDR_HEGIHT], 'big')
        self.HEIGHT = int.from_bytes(buf[IHDR_HEGIHT:IHDR_BITDEPTH], 'big')
        self.BITDEPTH = int.from_bytes(
            buf[IHDR_BITDEPTH:IHDR_COLORTYPE], 'big')
        self.COLORTYPE = int.from_bytes(
            buf[IHDR_COLORTYPE:IHDR_COMPTYPE], 'big')
        self.COMPTYPE = int.from_bytes(
            buf[IHDR_COMPTYPE:IHDR_FILTYPE], 'big')
        if self.COMPTYPE != 0:
            print("Invalid: Unknown compression method")
        self.FILTYPE = int.from_bytes(buf[IHDR_FILTYPE:IHDR_INTERLACE], 'big')
        if self.COMPTYPE != 0:
            print("Invalid: Unknown filter method")
        self.INTERLACE = int.from_bytes(
            buf[IHDR_INTERLACE:IHDR_CRC], 'big')
        crcData = int.from_bytes(buf[IHDR_CRC:IHDR_CRC + 4], 'big')
        crcCalc = zlib.crc32(buf[IHDR_HEAD:IHDR_INTERLACE + 1])
        if crcData != crcCalc:
            print("Invalid: This PNG is broken")
        self.CRC = crcData

        cursor = IHDR_CRC + 4
        pngData = b''
        isIDAT = True
        while (isIDAT):
            chunkSize = int.from_bytes(buf[cursor:cursor + CHUNK_STEP], 'big')
            chunkType = buf[cursor + CHUNK_STEP:cursor + CHUNK_STEP * 2]
            print("chunk type: " + chunkType.decode('utf8'))

            if chunkType == b'IEND':
                isIDAT = False
            elif chunkType == b'IDAT':
                pngData += buf[cursor + CHUNK_STEP *
                               2: cursor + CHUNK_STEP * 2 + chunkSize]

            cursor = cursor + chunkSize + CHUNK_STEP * 3

        print(len(pngData))

        decompressed_data = zlib.decompress(pngData)
        bitsPerPixel = self.__bitsPerPixel(self.COLORTYPE, self.BITDEPTH)
        bytesPerPixel = int(bitsPerPixel / 8)

        self.COMPDATA = pngData

        self.IMG = self.__applyFilter(
            decompressed_data, self.WIDTH, self.HEIGHT, bitsPerPixel, bytesPerPixel)

    def info(self):
        print("width    : " + str(self.WIDTH))
        print("height   : " + str(self.HEIGHT))
        print("depth    : " + str(self.BITDEPTH))
        print("colortype: " + str(self.COLORTYPE))
        print("interlace: " + str(self.INTERLACE))

    def __bitsPerPixel(self, colortype, depth=None):
        if colortype == 0:
            return depth
        elif colortype == 2:
            return depth * 3
        elif colortype == 3:
            return depth
        elif colortype == 4:
            return depth * 2
        elif colortype == 6:
            return depth * 4
        else:
            print("Invalid: Unknown color type.")

    def __applyFilter(self, decompressed_data, width, height, bitsPerPixel, bytesPerPixel):
        rowSize = int(bytesPerPixel * self.WIDTH + 1)
        data = [decompressed_data[h * rowSize:h * rowSize + rowSize]
                for h in range(self.HEIGHT)]
        data = [[c for c in data[h]] for h in range(self.HEIGHT)]
        prevRowData = [0]*rowSize
        for h in range(self.HEIGHT):
            rowData = data[h]
            filterType = rowData[0]

            currentScanData = rowData[1:]
            prevScanData = prevRowData[1:]

            if filterType == 0:
                continue
            elif filterType == 1:
                for i in range(bytesPerPixel, len(currentScanData)):
                    currentScanData[i] = (
                        currentScanData[i-bytesPerPixel] + currentScanData[i]) % 256
            elif filterType == 2:
                for i in range(0, len(currentScanData)):
                    currentScanData[i] = (
                        prevScanData[i] + currentScanData[i]) % 256
            elif filterType == 3:
                for i in range(bytesPerPixel):
                    currentScanData[i] = (currentScanData[i] +
                                          int(prevScanData[i] / 2)) % 256
                for i in range(bytesPerPixel, len(currentScanData)):
                    _ = int(
                        (currentScanData[i-bytesPerPixel] + prevScanData[i]) / 2)
                    currentScanData[i] = (_ + currentScanData[i]) % 256
            elif filterType == 4:
                a, b, c, Pr = 0, 0, 0, 0
                for i in range(bytesPerPixel):
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
                for i in range(bytesPerPixel, len(currentScanData)):
                    a = currentScanData[i - bytesPerPixel]
                    c = prevScanData[i - bytesPerPixel]
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

            data[h][1:] = currentScanData
            prevRowData = rowData

        return data

    def write(self, filepath):
        raw = b''
        raw += b'\x89' + 'PNG\r\n\x1a\n'.encode('ascii')
        raw += (13).to_bytes(4, 'big')
        raw += 'IHDR'.encode('ascii')
        raw += (self.WIDTH).to_bytes(4, 'big')
        raw += (self.HEIGHT).to_bytes(4, 'big')
        raw += (self.BITDEPTH).to_bytes(1, 'big')
        raw += (self.COLORTYPE).to_bytes(1, 'big')
        raw += (self.COMPTYPE).to_bytes(1, 'big')
        raw += (self.FILTYPE).to_bytes(1, 'big')
        raw += (self.INTERLACE).to_bytes(1, 'big')
        raw += (self.CRC).to_bytes(4, 'big')

        raw += (1).to_bytes(4, 'big')
        srgb = 'sRGB'.encode('ascii') + (3).to_bytes(1, 'big')
        raw += srgb + zlib.crc32(srgb).to_bytes(4, 'big')

        for i in self.IMG:
            i[0] = 0
        imgRaw = b''.join([(c).to_bytes(1, 'big')
                           for inner in self.IMG for c in inner])
        compressedData = zlib.compress(imgRaw)

        raw += (len(compressedData)).to_bytes(4, 'big')
        IDATData = b'IDAT' + compressedData
        raw += IDATData
        raw += zlib.crc32(IDATData).to_bytes(4, 'big')

        raw += (0).to_bytes(4, 'big')
        raw += 'IEND'.encode('ascii')
        raw += zlib.crc32(b'IEND').to_bytes(4, 'big')

        with open(filepath, 'wb') as f:
            f.write(raw)
            f.close()

    def getRGB(self):
        pass

    def getRGBA(self):
        pass

    def uncompress(self, data):
        pass


if __name__ == "__main__":
    p = PNG("../Assets/lenna.png")
    #p = PNG("test.png")
    p.write("test.png")
