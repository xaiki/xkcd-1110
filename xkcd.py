#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import math
import urllib

import gi
from gi.repository import GLib
from gi.repository import Clutter

Clutter.init(None)

# it'd be nice to have a better force model, but for now:
FORCE = 50
# for some reason Clutter is lying to us… well…
ACTOR_SIZE = 2048

smap = {'x':{-1:'e',1:'w'},'y':{1:'n',-1:'s'}}

# if you set this, all magic goes away
DEBUG=0

if DEBUG:
    sky_color = Clutter.Color.new(0,255,0,0)
    earth_color = Clutter.Color.new(255,0,0,0)

    debug_text = Clutter.Text()
    debug_text.set_text ("hello")
    debug_text.set_color (Clutter.Color.new(255,0,0,200))
else:
    sky_color = Clutter.Color.new(255,255,255,0)
    earth_color = Clutter.Color.new(0,0,0,0)

class XaMap:
    def __init__(self, tex=None, stage=None):
        self.current_tile = [0, 0]
        self.cache_dir = ".cache"
        self.base_url = "http://imgs.xkcd.com/clickdrag/"

        try:
            os.mkdir(self.cache_dir)
        except OSError:
            pass

        if (tex):
            self.tex = tex
        else:
            self.tex = ([self.new_col ( 1, 0, 0),
                         self.new_col ( 0, 0, 0),
                         self.new_col (-1, 0, 0)])

        print "DEBUG", tex

        if (stage):
            self.stage = stage
        else:
            self.stage = Clutter.Stage.get_default()
        self.stage_size = self.stage.get_size()
        self.stage.set_background_color (sky_color)
        self.stage.set_title ("XKCD: #1110")

        self.scroll = Clutter.Actor()
        self.scroll.add_action (Clutter.DragAction())
        self.scroll.set_reactive (True)

        for i in range(3):
            for j in range(3):
                self.show_tile(i, j)

        self.stage.add_actor (self.scroll)
        self.stage.show()
        if DEBUG:
            self.stage.add_actor (debug_text)

        self.scroll.set_position (0, -1100)
        self.stage.connect ("key-press-event", self.on_key_press, self.scroll)

    def new_col (self, direction, x, y):
            col = [self.new_tex (x + direction, y + 1),
                   self.new_tex (x + direction, y),
                   self.new_tex (x + direction, y - 1)]
            print "new col", col
            return col

    def new_row (self, direction, x, y):
            row = [self.new_tex (x + 1, y + direction),
                   self.new_tex (x    , y + direction),
                   self.new_tex (x - 1, y + direction)]
            return row

    def get_tile_filename (self, x, y):
        if (x<=0):
            x = x - 1
        if (y>=0):
            y = y + 1

        return "%d%c%d%c.png" % (abs(y), smap['y'][y/abs(y)], abs(x), smap['x'][x/abs(x)])

    def new_tex (self, x, y):
        print "loading tile for position: ", (x, y)
        f = self.get_tile_filename (x, y)
        f = self.check_cache (f)

        try:
            texture = Clutter.Texture.new_from_file (f)
            print (f, texture)
            return texture
        except (gi._glib.GError):
            print ("couldn't find %s: " % f)
            return None

    def check_cache (self, fn):
        try:
            os.stat (self.cache_dir + '/' + fn)
        except OSError:
            self.download ("http://imgs.xkcd.com/clickdrag/" + fn)

        return self.cache_dir + '/' + fn

    def download(self, url):
    	"""Copy the contents of a file from a given URL
    	to a local file.
    	"""

        print "downloading", url
    	web_file = urllib.urlopen(url)
    	cache_file = open(self.cache_dir + '/' + url.split('/')[-1], 'w')
    	cache_file.write(web_file.read())
    	web_file.close()
    	cache_file.close()

    def set_current_tile (self, tile):
        self.current_tile = tile
        if (tile[1] > 0):
            self.stage.set_background_color (sky_color)
        elif (tile[1] < 0):
            self.stage.set_background_color (earth_color)


    def show_tile (self, x, y):
        actor = self.tex[x][y]
        nx = (-self.current_tile[0] + x - 1)*ACTOR_SIZE
        ny = (-self.current_tile[1] + y - 1)*ACTOR_SIZE

        print "moving", actor, "to:", (x,y), self.current_tile, "to", nx, ny
        if not actor:
            print "No tile at", x, y
            return

        self.scroll.add_actor (actor)
        actor.set_position(nx, ny)

    def add_row (self, direction, row):
        if (direction != -1) and (direction != 1):
            raise ValueError

        for i in range(3):
            if self.tex[i][1+direction]:
                self.scroll.remove_actor(self.tex[i][1+direction])
            for j in range (2):
                if (direction == -1):
                    self.tex[i][j] = self.tex[i][j+1]
                else:
                    self.tex[i][2-j] = self.tex[i][1-j]
            self.tex[i][1-direction] = row[i]
            self.show_tile (i, 1-direction)

    def add_col (self, direction, col):
        if (direction != -1) and (direction != 1):
            raise ValueError

        for j in range(3):
            actor = self.tex[1+direction][j]
            if actor:
                self.scroll.remove_actor (actor)
                del(actor)
            for i in range (2):
                if (direction == -1):
                    self.tex[i][j] = self.tex[i+1][j]
                else:
                    self.tex[2-i][j] = self.tex[1-i][j]
            self.tex[1-direction][j] = col[j]
            self.show_tile (1-direction, j)

        print self.tex

    # this blocks the UI, we'd need a GAsync, to get the data and all, just cache it… =/
    def recenter (self, tile, motion):
        GLib.idle_add (self.do_recenter, (tile, motion))

    def do_recenter (self, args):
        tile, motion = args

        print "recentering", tile, motion
        self.set_current_tile(tile)

        if DEBUG:
            debug_text.set_text ("current Tile:" + str(tile) + get_tile_filename(*tile))
        if motion[0]:
            print "adding a col"
            self.add_col(motion[0], self.new_col(motion[0], *tile))
        if motion[1]:
            print "adding a row"
            self.add_row(motion[1], self.new_row(motion[1], *tile))

    def on_key_press (self, stage, event, actor):
        if event.keyval == Clutter.KEY_q:
            Clutter.main_quit()

        if event.keyval == Clutter.KEY_Up:
            actor.move_by (0, FORCE)

        if event.keyval == Clutter.KEY_Down:
            actor.move_by (0, -FORCE)

        if event.keyval == Clutter.KEY_Left:
            actor.move_by (FORCE, 0)

        if event.keyval == Clutter.KEY_Right:
            actor.move_by (-FORCE, 0)

        pos = actor.get_position()
        tile = [1 + int(math.floor((pos[i] - self.stage_size[i])/ACTOR_SIZE)) for i in range(2)]

#        print "keypress" tile, pos, self.stage_size, actor.get_size()
        if (tile != self.current_tile):
            motion = [tile[i] - self.current_tile[i] for i in range(2)]
            self.recenter (tile, motion)

def show_cb (actor, coord):
    x, y = coord
#    print "show:", coord

tex = XaMap()

Clutter.main()
