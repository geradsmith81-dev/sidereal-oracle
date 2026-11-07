"""QR codes for friend cards: a small, dependency-free encoder (ISO/IEC 18004).

Byte mode, error-correction level M (about 15 % of the code can be damaged and still read), versions 1-40, the mask
chosen by the standard's penalty rules. Used to show a friend card as a code a phone camera can scan.
Checked module-for-module against an independent encoder (K. Arase's QRCode library, MIT licence) in testing.
"""
import io

# error-correction codewords per block and number of blocks, level M, versions 1-40 (index 0 unused)
_ECC_M = [None, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28,
          28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28]
_BLOCKS_M = [None, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26,
             28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49]
_FORMAT_M = 0          # the two error-correction bits of level M in the format information

_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mul(a, b):
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _rs_divisor(degree):
    res = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(degree):
            res[j] = _mul(res[j], root)
            if j + 1 < degree:
                res[j] ^= res[j + 1]
        root = _mul(root, 2)
    return res


def _rs_remainder(data, div):
    res = [0] * len(div)
    for b in data:
        f = b ^ res.pop(0)
        res.append(0)
        for i, c in enumerate(div):
            res[i] ^= _mul(c, f)
    return res


def _raw_modules(ver):
    n = (16 * ver + 128) * ver + 64
    if ver >= 2:
        k = ver // 7 + 2
        n -= (25 * k - 10) * k - 55
        if ver >= 7:
            n -= 36
    return n


def _data_capacity(ver):
    return _raw_modules(ver) // 8 - _ECC_M[ver] * _BLOCKS_M[ver]


def _align_positions(ver):
    if ver == 1:
        return []
    k = ver // 7 + 2
    step = (ver * 8 + k * 3 + 5) // (k * 4 - 4) * 2
    size = ver * 4 + 17
    return [6] + sorted(size - 7 - i * step for i in range(k - 1))


class _Matrix:
    def __init__(self, ver):
        self.ver = ver
        self.size = ver * 4 + 17
        self.m = [[False] * self.size for _ in range(self.size)]
        self.fn = [[False] * self.size for _ in range(self.size)]

    def set(self, x, y, dark):
        self.m[y][x] = bool(dark)
        self.fn[y][x] = True


def _function_patterns(M):
    s = M.size
    for i in range(s):
        M.set(6, i, i % 2 == 0)
        M.set(i, 6, i % 2 == 0)
    for cx, cy in ((3, 3), (s - 4, 3), (3, s - 4)):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                x, y = cx + dx, cy + dy
                if 0 <= x < s and 0 <= y < s:
                    M.set(x, y, max(abs(dx), abs(dy)) not in (2, 4))
    pos = _align_positions(M.ver)
    n = len(pos)
    for i in range(n):
        for j in range(n):
            if (i, j) in ((0, 0), (0, n - 1), (n - 1, 0)):
                continue
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    M.set(pos[i] + dx, pos[j] + dy, max(abs(dx), abs(dy)) != 1)
    _format_bits(M, 0)
    if M.ver >= 7:
        rem = M.ver
        for _ in range(12):
            rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
        bits = M.ver << 12 | rem
        for i in range(18):
            b = (bits >> i) & 1
            a, c = s - 11 + i % 3, i // 3
            M.set(a, c, b)
            M.set(c, a, b)


def _format_bits(M, mask):
    data = _FORMAT_M << 3 | mask
    rem = data
    for _ in range(10):
        rem = (rem << 1) ^ ((rem >> 9) * 0x537)
    bits = (data << 10 | rem) ^ 0x5412
    s = M.size
    bit = lambda i: (bits >> i) & 1
    for i in range(6):
        M.set(8, i, bit(i))
    M.set(8, 7, bit(6))
    M.set(8, 8, bit(7))
    M.set(7, 8, bit(8))
    for i in range(9, 15):
        M.set(14 - i, 8, bit(i))
    for i in range(8):
        M.set(s - 1 - i, 8, bit(i))
    for i in range(8, 15):
        M.set(8, s - 15 + i, bit(i))
    M.set(8, s - 8, True)


def _codewords(data, ver):
    nblocks, ecclen = _BLOCKS_M[ver], _ECC_M[ver]
    raw = _raw_modules(ver) // 8
    nshort = nblocks - raw % nblocks
    shortlen = raw // nblocks
    div = _rs_divisor(ecclen)
    blocks, k = [], 0
    for i in range(nblocks):
        dat = data[k:k + shortlen - ecclen + (0 if i < nshort else 1)]
        k += len(dat)
        ecc = _rs_remainder(dat, div)
        if i < nshort:
            dat = dat + [0]
        blocks.append(dat + ecc)
    out = []
    for i in range(len(blocks[0])):
        for j, b in enumerate(blocks):
            if i != shortlen - ecclen or j >= nshort:
                out.append(b[i])
    return out


def _place(M, cw):
    s, i, right = M.size, 0, M.size - 1
    nbits = len(cw) * 8
    while right >= 1:
        if right == 6:
            right = 5
        for v in range(s):
            for j in range(2):
                x = right - j
                up = ((right + 1) & 2) == 0
                y = s - 1 - v if up else v
                if not M.fn[y][x] and i < nbits:
                    M.m[y][x] = bool((cw[i >> 3] >> (7 - (i & 7))) & 1)
                    i += 1
        right -= 2


_MASKS = [lambda x, y: (x + y) % 2 == 0, lambda x, y: y % 2 == 0, lambda x, y: x % 3 == 0,
          lambda x, y: (x + y) % 3 == 0, lambda x, y: (x // 3 + y // 2) % 2 == 0,
          lambda x, y: x * y % 2 + x * y % 3 == 0, lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
          lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0]


def _apply_mask(M, k):
    f = _MASKS[k]
    for y in range(M.size):
        for x in range(M.size):
            if not M.fn[y][x] and f(x, y):
                M.m[y][x] = not M.m[y][x]


def _penalty(m):
    s = len(m)
    p = 0
    lines = [row for row in m] + [[m[y][x] for y in range(s)] for x in range(s)]
    pat1 = [True, False, True, True, True, False, True, False, False, False, False]
    pat2 = pat1[::-1]
    for ln in lines:
        run, prev = 0, None
        for v in ln:
            if v == prev:
                run += 1
            else:
                if run >= 5:
                    p += 3 + run - 5
                run, prev = 1, v
        if run >= 5:
            p += 3 + run - 5
        for i in range(s - 10):
            seg = ln[i:i + 11]
            if seg == pat1 or seg == pat2:
                p += 40
    for y in range(s - 1):
        for x in range(s - 1):
            c = m[y][x]
            if c == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                p += 3
    dark = sum(sum(r) for r in m)
    p += abs(dark * 20 - s * s * 10) // (s * s) * 10
    return p


def encode(text, mask=None, version=None):
    """text (str) -> square list of rows of booleans (True = dark), without the quiet zone."""
    data = text.encode('utf-8')
    ver = version
    if ver is None:
        for v in range(1, 41):
            if 4 + (8 if v < 10 else 16) + 8 * len(data) <= _data_capacity(v) * 8:
                ver = v
                break
        else:
            raise ValueError('Too much text for a QR code.')
    cap = _data_capacity(ver) * 8
    bits = [0, 1, 0, 0]
    nb = 8 if ver < 10 else 16
    bits += [(len(data) >> i) & 1 for i in range(nb - 1, -1, -1)]
    for b in data:
        bits += [(b >> i) & 1 for i in range(7, -1, -1)]
    if len(bits) > cap:
        raise ValueError('Too much text for this QR version.')
    bits += [0] * min(4, cap - len(bits))
    bits += [0] * (-len(bits) % 8)
    pad = 0xEC
    while len(bits) < cap:
        bits += [(pad >> i) & 1 for i in range(7, -1, -1)]
        pad ^= 0xEC ^ 0x11
    words = [int(''.join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    cw = _codewords(words, ver)
    best = None
    for k in ([mask] if mask is not None else range(8)):
        M = _Matrix(ver)
        _function_patterns(M)
        _place(M, cw)
        _apply_mask(M, k)
        _format_bits(M, k)
        pen = _penalty(M.m) if mask is None else 0
        if best is None or pen < best[0]:
            best = (pen, M)
    return best[1].m


def png(text, scale=8, border=4, dark=(17, 25, 39), light=(255, 255, 255)):
    """PNG bytes of the QR code for text (dark on white, with the standard 4-module quiet zone)."""
    from PIL import Image
    m = encode(text)
    s = len(m)
    im = Image.new('RGB', (s + 2 * border, s + 2 * border), light)
    px = im.load()
    for y in range(s):
        for x in range(s):
            if m[y][x]:
                px[x + border, y + border] = dark
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    out = io.BytesIO()
    im.save(out, format='PNG', optimize=True)
    return out.getvalue()
