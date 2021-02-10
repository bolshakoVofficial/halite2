# Source: https://github.com/Mvwivs/halite2-deep-rl-bot

import math


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    @classmethod
    def polar(cls, r, ang):
        x = r * math.cos(math.radians(ang))
        y = r * math.sin(math.radians(ang))
        return cls(x, y)

    def __add__(self, p2):
        return Point(self.x + p2.x, self.y + p2.y)

    def __sub__(self, p2):
        return Point(self.x - p2.x, self.y - p2.y)

    def __eq__(self, other):
        if other == None:
            return False
        return self.x == other.x and self.y == other.y

    def norm2(self):
        return self.x ** 2 + self.y ** 2


class Seg:
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2

    # Returns the displacement vector from p1 to p2
    def d_vect(self):
        return self.p2 - self.p1

    # Returns the point of fraction t along the segment from p1 to p2
    def along_line(self, t):
        return Point((1 - t) * self.p1.x + t * self.p2.x, (1 - t) * self.p1.y + t * self.p2.y)


# PointPoint Distance Squared
def pp_dist2(p1, p2):
    return (p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2


# Point Point Distance
def pp_dist(p1, p2):
    return math.sqrt(pp_dist2(p1, p2))


# Dot Product
def dot(p1, p2):
    return p1.x * p2.x + p1.y * p2.y


# Point Segment Distance
def ps_dist(p, seg):
    v1 = p - seg.p1
    v2 = seg.d_vect()
    d = v2.norm2()

    if d == 0:
        return pp_dist(p, seg.p1)
    else:
        t = dot(v1, v2) / d
        if t < 0:
            t = 0
        elif t > 1:
            t = 1
        return pp_dist(p, seg.along_line(t))


# Min Distance Between two objects traveling on paths seg1 and seg2
def min_dist(seg1, seg2):
    start = seg2.p1 - seg1.p1
    delta = seg2.d_vect() - seg1.d_vect()
    seg_eff = Seg(start, start + delta)
    return ps_dist(Point(0, 0), seg_eff)
