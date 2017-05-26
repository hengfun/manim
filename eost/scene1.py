from mobject import Mobject, Group
from mobject.tex_mobject import TexMobject
from scene import Scene
from animation.simple_animations import *
from .widgets import *
import numpy as np
import helpers
from helpers import *
from animation.transform import *
from topics.geometry import *
from .matching import get_matching

def permute(l):
    import random
    ret = l[:]
    random.shuffle(ret)
    return ret

def permute_animations(mobj,move):
    mobjs = mobj.submobjects
    permuted_indices = np.random.permutation(len(mobjs))
    def path_along_arc(old_index,new_index):
        if ( (old_index < new_index and move == "down")
             or (new_index < old_index and move == "up")
             ):
            return counterclockwise_path()
        else:
            return clockwise_path()
    return [
        Transform(mobjs[i],mobjs[j].copy(),path_func=path_along_arc(i,j))
        for (i,j) in enumerate(permuted_indices)
    ]

class GrowFromCenterGeneral(Transform):
    def __init__(self, mobject, **kwargs):
        target = mobject.copy()
        mobject.scale_in_place(0)
        Transform.__init__(self, mobject, target, **kwargs)

def apple_pile():
    bottom_row = [Apple(i) for i in xrange(3)]
    top_row = [Apple(i) for i in xrange(3,5)]
    Group(*bottom_row).arrange_submobjects(buff=0.1)
    Group(*top_row).arrange_submobjects(buff=0.1)
    Group(*top_row).next_to(Group(*bottom_row),direction=UP,buff=0)
    return Group(*(bottom_row + top_row))

def pear_pile():
    bottom_two = [Pear(i) for i in xrange(2)]
    Group(*bottom_two).arrange_submobjects(buff=0.1)
    third_on_bottom = Pear(2).next_to(Group(*bottom_two),buff=0.1)
    top = (Pear(3)).next_to(Group(*bottom_two),direction=UP,buff=0)
    return Group(*(bottom_two + [third_on_bottom, top]))

class CountTransform(Succession):
    CONFIG = {
        'rate_func' : None
    }

    def __init__(self, mobject, target, direction):
        numbers=[]
        def transform(mobj,tgt,i):
            number = TextMobject(str(i+1)).next_to(tgt,direction=direction)
            numbers.append(number)
            return AnimationGroup(
                Write(number),
                Transform(mobj,tgt),
            )
        transforms = [
            transform(mobj,tgt,i)
            for (i,(mobj,tgt))
            in enumerate(zip(mobject.submobjects,target.submobjects))
        ]
        self.numbers = numbers
        Succession.__init__(self,*transforms)

    def summarize(self):
        central_number = self.numbers[-1].copy()
        central_number.shift(
            Group(*self.numbers).get_center()
            - central_number.get_center()
        )
        return AnimationGroup(*(
            [FadeOut(i) for i in self.numbers[:-1]]
            + [Transform(self.numbers[-1],central_number)]
        ))

class Scene1(Scene):
    def construct(self):
        apples = apple_pile().center()
        pears = pear_pile().center().next_to(apples,direction=DOWN)
        Group(apples,pears).center()
        # Display the two lines of apples and pears
        self.play(Succession(*map(GrowFromCenterGeneral, apples.submobjects), rate_func=None, run_time = 1.5*DEFAULT_ANIMATION_RUN_TIME))
        self.play(Succession(*map(GrowFromCenterGeneral, pears.submobjects), rate_func=None, run_time = 1.5*DEFAULT_ANIMATION_RUN_TIME))
        self.dither()
        counted_apples = [Apple(i) for i in xrange(5)]
        counted_pears = [Pear(i) for i in xrange(4)]
        counted_apple_group = Group(*counted_apples).arrange_submobjects().to_edge(UP)
        counted_pear_group = Group(*counted_pears).arrange_submobjects().to_edge(DOWN)
        apple_count = CountTransform(apples,counted_apple_group,direction=DOWN)
        self.play(apple_count)
        pear_count = CountTransform(pears,counted_pear_group,direction=UP)
        self.play(pear_count)
        self.play(apple_count.summarize(),pear_count.summarize())
        inequality = TexMobject(
            apple_count.numbers[-1].args[0],
            ">",
            pear_count.numbers[-1].args[0]
        ).center()
        self.play(
            Transform(
                apple_count.numbers[-1],
                inequality.get_part_by_tex(apple_count.numbers[-1].args[0])
            ),
            Write(inequality.get_part_by_tex(">")),
            Transform(
                pear_count.numbers[-1],
                inequality.get_part_by_tex(pear_count.numbers[-1].args[0])
            )
        )
        self.dither()
        self.play(*map(FadeOut,[
            apple_count.numbers[-1],
            inequality,
            pear_count.numbers[-1]
        ]))
        # Show a matching
        matching = get_matching(Group(*apples),Group(*pears))
        self.play(ShowCreation(matching))
        self.emphasize(apples[-1]) # Above, I pretended like this function
                                   # was generic over the number of apples
                                   # pears.  But here, and in the emphasis
                                   # below, it isn't.
        self.play(Uncreate(matching))
        # Permute them
        apple_permutations=permute_animations(apples,move="down")
        pear_permutations=permute_animations(pears,move="up")
        self.play(*(apple_permutations + pear_permutations))
        # Show a different matching
        permuted_apples = permute(apples)
        permuted_pears = permute(pears)
        matching = get_matching(Group(*permuted_apples),Group(*permuted_pears))
        self.play(ShowCreation(matching))
        self.emphasize(permuted_apples[-1]) # See comment above. This [-1] is
                                            # kind of a cheat
        self.play(Uncreate(matching))
        self.dither()

    # Emphasize an apple mobj by making it slightly bigger and white
    def emphasize(self,apple):
        orig = apple.copy()
        emphasized = Apple(color=WHITE)
        emphasized.shift(orig.get_center() - emphasized.get_center())
        emphasized.scale_in_place(1.1)
        self.play(Transform(apple,emphasized))
        self.play(Transform(apple,orig))