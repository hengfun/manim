from helpers import *

from mobject import Mobject
from mobject.vectorized_mobject import VMobject

class Arc(VMobject):
    CONFIG = {
        "radius"           : 1.0,
        "start_angle"      : 0,
        "num_anchors"      : 9,
        "anchors_span_full_range" : True,
    }
    def __init__(self, angle, **kwargs):
        digest_locals(self)
        VMobject.__init__(self, **kwargs)

    def generate_points(self):
        self.set_anchor_points(
            self.get_unscaled_anchor_points(),
            mode = "smooth"
        )
        self.scale(self.radius)

    def get_unscaled_anchor_points(self):
        return [
            np.cos(a)*RIGHT+np.sin(a)*UP
            for a in np.linspace(
                self.start_angle, 
                self.start_angle + self.angle, 
                self.num_anchors
            )
        ]

    def add_tip(self, tip_length = 0.25):
        #TODO, do this a better way
        arrow = Arrow(*self.points[-2:], tip_length = tip_length)
        self.add(arrow.split()[-1])
        self.highlight(self.get_color())
        return self


class Circle(Arc):
    CONFIG = {
        "color" : RED,
        "close_new_points" : True,
        "anchors_span_full_range" : False
    }
    def __init__(self, **kwargs):
        Arc.__init__(self, 2*np.pi, **kwargs)

class Dot(Circle): #Use 1D density, even though 2D
    CONFIG = {
        "radius"       : 0.08,
        "stroke_width" : 0,
        "fill_opacity" : 1.0,
        "color" : WHITE
    }
    def __init__(self, point = ORIGIN, **kwargs):
        Circle.__init__(self, **kwargs)
        self.shift(point)
        self.init_colors()


class Line(VMobject):
    CONFIG = {
        "buff" : 0,
        "considered_smooth" : False,
        "path_arc" : None,
        "n_arc_anchors" : 10, #Only used if path_arc is not None
    }
    def __init__(self, start, end, **kwargs):
        digest_config(self, kwargs)
        self.set_start_and_end(start, end)
        VMobject.__init__(self, **kwargs)

    def generate_points(self):
        if self.path_arc is None:
            self.set_points_as_corners([self.start, self.end])
        else:
            path_func = path_along_arc(self.path_arc)
            self.set_points_smoothly([
                path_func(self.start, self.end, alpha)
                for alpha in np.linspace(0, 1, self.n_arc_anchors)
            ])
            self.considered_smooth = True
        self.account_for_buff()

    def account_for_buff(self):
        anchors = self.get_anchors()
        length = sum([
            np.linalg.norm(a2-a1)
            for a1, a2 in zip(anchors, anchors[1:])
        ])
        if length < 2*self.buff or self.buff == 0:
            return
        buff_proportion = self.buff / length
        self.pointwise_become_partial(
            self, buff_proportion, 1 - buff_proportion
        )

    def set_start_and_end(self, start, end):
        start_to_end = self.pointify(end) - self.pointify(start)
        vect = np.zeros(len(start_to_end))
        longer_dim = np.argmax(map(abs, start_to_end))
        vect[longer_dim] = start_to_end[longer_dim]
        self.start, self.end = [
            arg.get_edge_center(unit*vect)
            if isinstance(arg, Mobject)
            else np.array(arg)
            for arg, unit in zip([start, end], [1, -1])
        ]

    def pointify(self, mob_or_point):
        if isinstance(mob_or_point, Mobject):
            return mob_or_point.get_center()
        return np.array(mob_or_point)

    def get_length(self):
        start, end = self.get_start_and_end()
        return np.linalg.norm(start - end)

    def get_start_and_end(self):
        return self.get_start(), self.get_end()

    def get_start(self):
        return self.points[0]

    def get_end(self):
        return self.points[-1]

    def get_slope(self):
        start, end = self.get_start_and_end()
        rise, run = [
            float(end[i] - start[i])
            for i in [1, 0]
        ]
        return np.inf if run == 0 else rise/run

    def get_angle(self):
        start, end = self.get_start_and_end()
        return angle_of_vector(end-start)

    def put_start_and_end_on(self, new_start, new_end):
        epsilon = 0.01
        if self.get_length() == 0:
            #TODO, this is hacky
            self.points[0] += epsilon*LEFT
        new_length = np.linalg.norm(new_end - new_start)
        new_length = max(new_length, epsilon)
        new_angle = angle_of_vector(new_end - new_start)
        self.scale(new_length / self.get_length())
        self.rotate(new_angle - self.get_angle())
        self.shift(new_start - self.get_start())
        return self

class DashedLine(Line):
    CONFIG = {
        "dashed_segment_length" : 0.05
    }
    def __init__(self, *args, **kwargs):
        self.init_kwargs = kwargs
        Line.__init__(self, *args, **kwargs)

    def generate_points(self):
        length = np.linalg.norm(self.end-self.start)
        num_interp_points = int(length/self.dashed_segment_length)
        points = [
            interpolate(self.start, self.end, alpha)
            for alpha in np.linspace(0, 1, num_interp_points)
        ]
        includes = it.cycle([True, False])
        for p1, p2, include in zip(points, points[1:], includes):
            if include:
                self.add(Line(p1, p2, **self.init_kwargs))
        self.put_start_and_end_on(self.start, self.end)
        return self

    def get_start(self):
        if len(self) > 0:
            return self[0].points[0]
        else:
            return self.start

    def get_end(self):
        if len(self) > 0:
            return self[-1].points[-1]
        else:
            return self.end

class DashedMobject(VMobject):
    CONFIG = {
        "dashes_num" : 15,
        "spacing"    : 0.5,
        "color"      : WHITE
    }
    def __init__(self, mob, **kwargs):
        digest_locals(self)
        VMobject.__init__(self, **kwargs)

        segment_len = (1-float(self.spacing)) / self.dashes_num

        for i in range(self.dashes_num):
            a = float(i) / self.dashes_num
            b = a + segment_len
            dash = VMobject(color = self.color)
            dash.pointwise_become_partial(mob, a, b)
            self.submobjects.append(dash)

class GradientLine(Line):
    CONFIG = {
        "segment_num" : 200
    }
    def __init__(self, start, end, *colors, **kwargs):
        self.init_kwargs = kwargs
        Line.__init__(self, start, end, **kwargs)
        self.gradient_highlight(*colors)

    def generate_points(self):
        points = [
            interpolate(self.start, self.end, alpha)
            for alpha in np.linspace(0, 1, self.segment_num+1)
        ]
        for p1, p2 in zip(points, points[1:]):
            self.add(Line(p1, p2, **self.init_kwargs))

        return self

    def get_start(self):
        if len(self) > 0:
            return self[0].points[0]
        else:
            return self.start

    def get_end(self):
        if len(self) > 0:
            return self[-1].points[-1]
        else:
            return self.end

class Arrow(Line):
    CONFIG = {
        "color"      : YELLOW_C,
        "tip_length" : 0.25,
        "tip_angle"  : np.pi/6,
        "buff"       : MED_SMALL_BUFF,
        "propogate_style_to_family" : False,
        "preserve_tip_size_when_scaling" : True,
    }
    def __init__(self, *args, **kwargs):
        points = map(self.pointify, args)
        if len(args) == 1:
            args = (points[0]+UP+LEFT, points[0])
        Line.__init__(self, *args, **kwargs)
        self.add_tip()

    def add_tip(self, add_at_end = True):
        tip = VMobject(
            close_new_points = True,
            mark_paths_closed = True,
            fill_color = self.color,
            fill_opacity = 1,
            stroke_color = self.color,
        )
        self.set_tip_points(tip, add_at_end)
        self.tip = tip
        self.add(self.tip)
        self.init_colors()

    def set_tip_points(self, tip, add_at_end = True):
        start, end = self.get_start_and_end()
        anchors = self.get_anchors()
        vect = anchors[-1] - anchors[-2]
        vect *= -self.tip_length / np.linalg.norm(vect)
        if not add_at_end:
            start, end = end, start
            vect = -vect
        tip_points = [
            end+rotate_vector(vect, u*self.tip_angle)
            for u in 1, -1
        ]
        tip.set_anchor_points(
            [tip_points[0], end, tip_points[1]],
            mode = "corners"
        )
        return self

    def get_end(self):
        if hasattr(self, "tip"):
            return self.tip.get_anchors()[1]
        else:
            return Line.get_end(self)

    def get_tip(self):
        return self.tip

    def scale(self, scale_factor, **kwargs):
        Line.scale(self, scale_factor, **kwargs)
        if self.preserve_tip_size_when_scaling and self.get_length() > self.tip_length:
            self.set_tip_points(self.tip)
        return self

class Vector(Arrow):
    CONFIG = {
        "color" : YELLOW,
        "buff"  : 0,
    }
    def __init__(self, direction, **kwargs):
        if len(direction) == 2:
            direction = np.append(np.array(direction), 0)
        Arrow.__init__(self, ORIGIN, direction, **kwargs)

class DoubleArrow(Arrow):
    def __init__(self, *args, **kwargs):
        Arrow.__init__(self, *args, **kwargs)
        self.add_tip(add_at_end = False)


class Cross(VMobject):
    CONFIG = {
        "color"  : YELLOW,
        "propogate_style_to_family" : True,
        "radius" : 0.3,
    }
    def generate_points(self):
        p1, p2, p3, p4 = self.radius * np.array([
            UP+LEFT, 
            DOWN+RIGHT,
            UP+RIGHT, 
            DOWN+LEFT,
        ])
        self.add(Line(p1, p2), Line(p3, p4))
        self.init_colors()

class CubicBezier(VMobject):
    def __init__(self, points, **kwargs):
        VMobject.__init__(self, **kwargs)
        self.set_points(points)

class Polygon(VMobject):
    CONFIG = {
        "color" : GREEN_D,
        "mark_paths_closed" : True,
        "close_new_points" : True,
        "considered_smooth" : False,
    }
    def __init__(self, *vertices, **kwargs):
        assert len(vertices) > 1
        digest_locals(self)
        VMobject.__init__(self, **kwargs)

    def generate_points(self):
        self.set_anchor_points(self.vertices, mode = "corners")

    def get_vertices(self):
        return self.get_anchors_and_handles()[0]

class PolyLine(Polygon):
    CONFIG = {
        "mark_paths_closed" : False,
        "close_new_points" : False,
    }

class RegularPolygon(Polygon):
    CONFIG = {
        "start_angle" : 0
    }
    def __init__(self, n = 3, **kwargs):
        digest_config(self, kwargs, locals())
        start_vect = rotate_vector(RIGHT, self.start_angle)
        vertices = compass_directions(n, start_vect)
        Polygon.__init__(self, *vertices, **kwargs)


class Rectangle(VMobject):
    CONFIG = {
        "color"  : WHITE,
        "height" : 2.0,
        "width"  : 4.0,
        "mark_paths_closed" : True,
        "close_new_points" : True,
        "considered_smooth" : False,
    }
    def generate_points(self):
        y, x = self.height/2., self.width/2.
        self.set_anchor_points([
            x*LEFT+y*UP,
            x*RIGHT+y*UP,
            x*RIGHT+y*DOWN,
            x*LEFT+y*DOWN
        ], mode = "corners")

class Square(Rectangle):
    CONFIG = {
        "side_length" : 2.0,
    }
    def __init__(self, **kwargs):
        digest_config(self, kwargs)
        Rectangle.__init__(
            self, 
            height = self.side_length,
            width = self.side_length,
            **kwargs
        )

class SurroundingRectangle(Rectangle):
    CONFIG = {
        "color" : YELLOW,
        "buff" : SMALL_BUFF,
    }
    def __init__(self, mobject, **kwargs):
        digest_config(self, kwargs)
        kwargs["width"] = mobject.get_width() + 2*self.buff
        kwargs["height"] = mobject.get_height() + 2*self.buff
        Rectangle.__init__(self, **kwargs)
        self.move_to(mobject)

class BackgroundRectangle(SurroundingRectangle):
    CONFIG = {
        "color" : BLACK,
        "stroke_width" : 0,
        "fill_opacity" : 0.75,
        "buff" : 0
    }
    def __init__(self, mobject, **kwargs):
        SurroundingRectangle.__init__(self, mobject, **kwargs)
        self.original_fill_opacity = self.fill_opacity

    def pointwise_become_partial(self, mobject, a, b):
        self.set_fill(opacity = b*self.original_fill_opacity)
        return self

    def get_fill_color(self):
        return Color(self.color)


class FullScreenFadeRectangle(Rectangle):
    CONFIG = {
        "height" : 2*SPACE_HEIGHT,
        "width" : 2*SPACE_WIDTH,
        "stroke_width" : 0,
        "fill_color" : BLACK,
        "fill_opacity" : 0.7,
    }

class ScreenRectangle(Rectangle):
    CONFIG = {
        "width_to_height_ratio" : 16.0/9.0,
        "height" : 4,
    }
    def generate_points(self):
        self.width = self.width_to_height_ratio * self.height
        Rectangle.generate_points(self)

class PictureInPictureFrame(Rectangle):
    CONFIG = {
        "height" : 3,
        "aspect_ratio" : (16, 9)
    }
    def __init__(self, **kwargs):
        digest_config(self, kwargs)
        height = self.height
        if "height" in kwargs:
            kwargs.pop("height")
        Rectangle.__init__(
            self,
            width = self.aspect_ratio[0],
            height = self.aspect_ratio[1],
            **kwargs
        )
        self.scale_to_fit_height(height)
        

class Grid(VMobject):
    CONFIG = {
        "height" : 6.0,
        "width"  : 6.0,
        "considered_smooth" : False,
    }
    def __init__(self, rows, columns, **kwargs):
        digest_config(self, kwargs, locals())
        VMobject.__init__(self, **kwargs)

    def generate_points(self):
        x_step = self.width / self.columns
        y_step = self.height / self.rows

        for x in np.arange(0, self.width+x_step, x_step):
            self.add(Line(
                [x-self.width/2., -self.height/2., 0],
                [x-self.width/2., self.height/2., 0],
            ))
        for y in np.arange(0, self.height+y_step, y_step):
            self.add(Line(
                [-self.width/2., y-self.height/2., 0],
                [self.width/2., y-self.height/2., 0]
            ))



