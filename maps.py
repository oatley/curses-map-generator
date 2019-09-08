#!/usr/bin/env python3
import time
import curses
import random
import os
import json
import gzip
import math
import re
from datetime import datetime
from curses import wrapper

# Globals
WALL_TYPE = 'wall'
FLOOR_TYPE = 'floor'
WALLCH = '#'
FLOORCH = '.'
WIN_HEIGHT = 1
WIN_WIDTH = 80
MAP_HEIGHT = 24
MAP_WIDTH = 70

# Object used for each tile on the screen. Used to store data relating to tiles
# such as the tile type, adjacent tile positions, or costs for pathfinding
class Tile:
    def __init__(self, y, x, c):
        self.y = y
        self.x = x
        self.ch = c
        self.neighbors = list()

    def update_neighbors(self, game_objects):
        self.neighbors = list()
        possible_neighbors = {(self.y+1,self.x), (self.y-1,self.x), (self.y,self.x+1), (self.y,self.x-1)}
        for y,x in possible_neighbors:
            try:
                key = get_yx_key(y,x)
                if game_objects[key]:
                    self.neighbors.append(key)
            except KeyError:
                pass

# Shortcut to make wall tile object
def add_wall(y, x):
    a = Tile(y, x, WALLCH)
    return a

# Shortcut to make floor tile object
def add_floor(y, x):
    a = Tile(y, x, FLOORCH)
    return a

# Custom classes are not serializable in json(could use _dict_?), create an easy to serialize data structure
# Might be better to make a custom json encoder object, but this works for prototype
def json_to_tile(jt):
    tile = Tile(jt['y'], jt['x'], jt['c'])
    tile.neighbors = jt['neighbors']
    return tile

# Custom classes are not serializable in json(could use _dict_?), create an easy to serialize data structure
# Might be better to make a custom json encoder object, but this works for prototype
def tile_to_json(tile):
    jt = dict()
    jt['x'] = tile.x
    jt['y'] = tile.y
    jt['c'] = tile.ch
    jt['neighbors'] = tile.neighbors
    return jt

def get_yx_key(y,x):
    return str(y)+"x"+str(x)

def get_tile_key(tile):
    return str(tile.y)+"x"+ str(tile.x)

# Creates a new map using voronoi regions, currently slow: 20 seconds for 100x100, 5-10 min for 300x300
def gen_map(sizey, sizex, midy, midx):
    # Timer for map generation
    t = time.process_time()
    totaltime = 0.0
    # Initialize loading screen window
    loadwin = curses.newwin(MAP_HEIGHT, MAP_WIDTH, 0, 0)
    loadwin.clear()
    loadwin.refresh()
    # Values for loading bars
    loadvalue = 1
    loadmax = sizey * sizex
    # Generate a solid grid of wall game objects for each tile position
    game_objects = {'mapsize': {'y': sizey,'x': sizex, 'c': '$', 'neighbors': []}, 'player': {'y': sizey,'x': sizex, 'c': 'P', 'neighbors': []}}
    for x in range(0, sizey):
        totaltime = time.process_time() - t
        percent = int((loadvalue / loadmax) * 100)
        loadwin.addstr(1, 1, '[Generating tiles] -> ' + str(percent) + '%')
        loadwin.addstr(2, 1, '[Generating V-Regions] -> 0%')
        loadwin.addstr(3, 1, '[Converting tiles -> V-Regions] -> 0%')
        loadwin.addstr(4, 1, '[Pathfinding -> link adjacent tiles] -> 0%')
        loadwin.addstr(5, 1, '[Total Time]:' + str(int(totaltime)))
        loadwin.border(0)
        loadwin.refresh()
        for y in range(0, sizex):
            tmp = add_wall(y, x)
            game_objects[get_tile_key(tmp)] = tmp
            loadvalue += 1
    # Values for loading bars, randomness adds to custom maps, and scales with large or small maps
    num = int ((sizex + sizey) / 2)
    regions = random.randrange(num,num*2)
    loadvalue = 1
    loadmax = regions
    # Pick random spots in grid map to become v regions
    v_regions = []
    for i in range(0,regions):
        totaltime = time.process_time() - t
        percent = int((loadvalue / loadmax) * 100)
        loadwin.addstr(1, 1, '[Generating tiles] -> 100%')
        loadwin.addstr(2, 1, '[Generating V-Regions] -> ' + str(percent) + '%')
        loadwin.addstr(3, 1, '[Converting tiles -> V-Regions] -> 0%')
        loadwin.addstr(4, 1, '[Pathfinding -> link adjacent tiles] -> 0%')
        loadwin.addstr(5, 1, '[Total Time]:' + str(int(totaltime)))
        loadwin.border(0)
        loadwin.refresh()
        rand_y = random.randrange(0, sizey)
        rand_x = random.randrange(0, sizex)
        rand_type = random.randrange(0,2)
        if rand_type == 1:
            v_regions.append(add_floor(rand_y, rand_x))
        else:
            v_regions.append(add_wall(rand_y, rand_x))
        loadvalue += 1
    v_regions.append(add_floor(midy, midx)) # player spawn position must be floor
    # Values for loading bars, randomness adds to custom maps, and scales with large or small maps
    percent = 1
    loadvalue = 1
    loadmax = sizex * sizey * regions
    # Convert all game obaects to closest voronoi region type (floor or wall)
    for key in game_objects.keys():
        if key == "player" or key == "mapsize":
            continue
        totaltime = time.process_time() - t
        closest = v_regions[0]
        percent = int((loadvalue / loadmax) * 100)
        loadwin.addstr(1, 1, '[Generating tiles] -> 100%')
        loadwin.addstr(2, 1, '[Generating V-Regions] -> 100%')
        loadwin.addstr(3, 1, '[Converting tiles -> V-Regions] -> ' + str(percent) + '%')
        loadwin.addstr(4, 1, '[Pathfinding -> link adjacent tiles] -> 0%')
        loadwin.addstr(5, 1, '[Total Time]:' + str(int(totaltime)))
        loadwin.border(0)
        loadwin.refresh()
        y = game_objects[key].y
        x = game_objects[key].x
        for v in v_regions:
            diff = math.sqrt((v.x-x)**2) + math.sqrt((v.y-y)**2)
            olddiff = math.sqrt((closest.x-x)**2) + math.sqrt((closest.y-y)**2)
            # Make walls around end of map
            if y >= sizey-1 or y <= 0 or x >= sizex-1 or x <= 0:
                game_objects[key].ch = WALLCH
            elif diff < olddiff:
                closest = v
                game_objects[key].ch = closest.ch
            loadvalue += 1
    # Values for loading bars
    percent = 1
    loadvalue = 1
    loadmax = sizex * sizey
    # Initialize tiles to know adjacent tiles neighbors, for pathfinding costing later
    for key in game_objects.keys():
        if key == "player" or key == "mapsize":
            continue
        totaltime = time.process_time() - t
        closest = v_regions[0]
        percent = int((loadvalue / loadmax) * 100)
        loadwin.addstr(1, 1, '[Generating tiles] -> 100%')
        loadwin.addstr(2, 1, '[Generating V-Regions] -> 100%')
        loadwin.addstr(3, 1, '[Converting tiles -> V-Regions] -> 100%')
        loadwin.addstr(4, 1, '[Pathfinding -> link adjacent tile] -> ' + str(percent) + '%')
        loadwin.addstr(5, 1, '[Total Time]:' + str(int(totaltime)))
        loadwin.border(0)
        loadwin.refresh()
        # All neighbor updating is moved to the tile objects for reuse later
        game_objects[key].update_neighbors(game_objects)
        loadvalue += 1
    del loadwin
    return game_objects

# Save game_objects to a compress json file at path
def save_map(path, game_objects):
    # Inialize load bar window and values
    loadwin = curses.newwin(MAP_HEIGHT, MAP_WIDTH, 0, 0)
    loadvalue = 1
    loadmax = len(game_objects.keys())
    loadwin.clear()
    loadwin.refresh()
    # Converts tiles data structure into a json safe writable data structure
    go = {'mapsize': game_objects['mapsize'], 'player': game_objects['player']}
    for key in game_objects.keys():
        if key == "player" or key == "mapsize":
            continue
        go[key] = tile_to_json(game_objects[key])
        # Load bar
        percent = int((loadvalue / loadmax) * 100)
        loadvalue += 1
        loadwin.addstr(1, 1, '[Converting objects to file format] -> ' + str(percent) + '%')
        loadwin.border(0)
        loadwin.refresh()
    # Values for loading bars
    loadvalue = 1
    loadmax = len(game_objects.keys())
    loadwin.addstr(2, 1, '[Compressing and writing '+path+']')
    loadwin.refresh()
    dirs = ['resources', 'resources/maps', 'resources/html_maps']
    for dir in dirs:
        try:
            os.mkdir(dir)
        except:
            pass
    # Compress, json, and write the data structure to a file
    with gzip.GzipFile(path, 'w') as fout:
        fout.write(json.dumps(go).encode('utf-8'))
    # Wait for user input
    loadwin.addstr(3, 1, 'press enter to continue...')
    c = loadwin.getch()
    loadwin.clear()
    loadwin.refresh()
    del loadwin

# Load compressed json file, return as game_objects
def load_map(path):
    # Inialize load bar window and values
    loadwin = curses.newwin(MAP_HEIGHT, MAP_WIDTH, 0, 0)
    loadwin.clear()
    loadwin.border(0)
    loadwin.addstr(1, 1, '[Decompressing and loading '+path+']')
    loadwin.refresh()
    # Decompress, store json into game_objects
    with gzip.GzipFile(path) as fin:
        go = json.loads(fin.read().decode('utf-8'))
    game_objects = {'mapsize': go['mapsize'], 'player': go['player']}
    # Inialize load bar window and values
    loadvalue = 1
    loadmax = len(go.keys()) - 2
    # Convert json object data into tile objects and store them in game_objects
    for key in go.keys():
        if key == "player" or key == "mapsize":
            continue
        game_objects[key] = json_to_tile(go[key])
        # Load bar
        percent = int((loadvalue / loadmax) * 100)
        loadvalue += 1
        loadwin.addstr(2, 1, '[Converting data to game objects] -> ' + str(percent) + '%')
        loadwin.border(0)
        loadwin.refresh()
    # Wait for user input
    loadwin.addstr(3, 1, 'press enter to continue...')
    c = loadwin.getch()
    loadwin.clear()
    loadwin.refresh()
    del loadwin
    return game_objects

# Scan the game_objects and convert it to a asci html viewable version
def html_map_export(sizey, sizex, game_objects):
    dateobj = datetime.now()
    date = dateobj.strftime('%y-%m-%d-%H-%M-%S')
    filename = 'resources/html_maps/map-' + date + '.html'
    f = open(filename, 'w')
    f.write('<!DOCTYPE html>\n<html>\n<head>\n<style>body{font-family: monospace; font-size: 10px;}</style>\n</head>\n<body>')
    for y in range(-sizey, sizey):
        if y != -sizey:
            f.write('\n')
        for x in range(-sizex, sizex):
            f.write(game_objects['tiles'][(y,x)].ch)
    f.write('</body>\n</html>')
    f.close()

# Main menu for selecting program action
def menu():
    mapsizey = 100
    mapsizex = 100
    menu = curses.newwin(MAP_HEIGHT, MAP_WIDTH, 0, 0)
    menu.clear()
    menu.nodelay(False)
    menu.clear()
    menu.border(0)
    menu.refresh()
    while True:
        curses.curs_set(False)
        menu.border(0)
        menu.addstr(1, 1, 'G - generate new map')
        menu.addstr(2, 1, 'L - load map')
        menu.addstr(3, 1, 'Q - quit program')
        menu.refresh()
        c = menu.getch()
        curses.flushinp() # clear other things besides getch?
        game_objects = {}
        if c == ord('g') or c == ord('G'):
            # delete map, make new map
            midy = int(MAP_HEIGHT / 2)
            midx = int(MAP_WIDTH / 2)
            menu.clear()
            menu.refresh()
            path = get_map_path()
            size = get_map_size()
            mapsizey = size
            mapsizex = size
            game_objects = gen_map(mapsizey, mapsizex, midy, midx)
            menu.clear()
            menu.refresh()
            save_map(path, game_objects)
            """
            try:
                save_map(path, game_objects)
            except:
                menu.clear()
                menu.addstr(MAP_HEIGHT-2, 1, 'error: failed to save map file (path or permissions?)')
                continue
            """
            menu.clear()
            menu.refresh()
            #html_map_export(mapsizey, mapsizex, game_objects)
        elif c == ord('l') or c == ord('L'):
            # load current map1
            game_objects = {}
            path = load_map_path()
            game_objects = load_map(path)
            """
            try:
                game_objects = load_map(path)
            except:
                menu.clear()
                menu.addstr(MAP_HEIGHT-2, 1, 'error: failed to load map file (possible corruption?)')
                continue
            """
        elif c == ord('q') or c == ord('Q'):
            exit(0)
        menu.clear()
        menu.refresh()
        del menu
        return game_objects

# Curses sub menu to get a filename from the user for map generation
def get_map_path():
    menu = curses.newwin(MAP_HEIGHT, MAP_WIDTH, 0, 0)
    menu.clear()
    menu.nodelay(False)
    strfilename = 'Enter a filename: '
    s = ''
    while s == '':
        menu.clear()
        curses.echo()
        curses.curs_set(True)
        menu.move(1, len(strfilename)+1)
        menu.border(0)
        menu.addstr(1,1,strfilename)
        menu.refresh()
        s = menu.getstr(1, len(strfilename)+1)
        s = s.decode('utf8').replace(' ', '').strip()
        path = 'resources/maps/' + s + '.map'
        if os.path.exists(path):
            menu.addstr(2,1, 'error: filename "'+ path +'" already exists')
            path = ''
            s = ''
            curses.noecho()
            curses.curs_set(False)
            menu.refresh()
            time.sleep(2)
            continue
        elif not re.match('^[\w]+$', s):
            menu.addstr(2,1, 'error: filename must use only letters and numbers')
            path = ''
            s = ''
            curses.noecho()
            curses.curs_set(False)
            menu.refresh()
            time.sleep(2)
            continue
        menu.addstr(2,1, 'selecting filename: ' + path)
        curses.noecho()
        curses.curs_set(False)
        menu.refresh()
        time.sleep(2)
        return path

# Curses sub menu to get a map size from user for map generation
def get_map_size():
    menu = curses.newwin(MAP_HEIGHT, MAP_WIDTH, 0, 0)
    menu.clear()
    menu.nodelay(False)
    strsize = 'Size: '
    s = ''
    while s == '':
        menu.clear()
        curses.echo()
        curses.curs_set(True)
        menu.move(2, len(strsize)+1)
        menu.border(0)
        menu.addstr(1,1, 'Size of map must be 50 or greater. (300 == 5+min)')
        menu.addstr(2,1,strsize)
        menu.refresh()
        s = menu.getstr(2, len(strsize)+1)
        s = s.decode('utf8').replace(' ', '').strip()
        if not re.match('^[\d]+$', s):
            menu.addstr(3,1, 'error: '+str(s)+' not integer')
            s = ''
            curses.noecho()
            curses.curs_set(False)
            menu.refresh()
            time.sleep(2)
            continue
        elif int(s) < 50:
            menu.addstr(3,1, 'error: '+str(s)+' must be >= 50')
            s = ''
            curses.noecho()
            curses.curs_set(False)
            menu.refresh()
            time.sleep(2)
            continue
        s = int(s)
        menu.addstr(3,1, 'integer size accepted: ' + str(s))
        curses.noecho()
        curses.curs_set(False)
        menu.refresh()
        time.sleep(2)
        return s

# Curses sub menu to get a filename from user for map loading
def load_map_path():
    menu = curses.newwin(MAP_HEIGHT, MAP_WIDTH, 0, 0)
    menu.clear()
    menu.nodelay(False)
    strfilename = 'Enter a filename to load: '
    s = ''
    while s == '':
        menu.clear()
        curses.echo()
        curses.curs_set(True)
        menu.move(1, len(strfilename)+1)
        menu.border(0)
        menu.addstr(1,1,strfilename)
        menu.refresh()
        s = menu.getstr(1, len(strfilename)+1)
        s = s.decode('utf8').replace(' ', '').strip()
        path = 'resources/maps/' + s + '.map'
        if not os.path.exists(path):
            menu.addstr(2,1, 'error: filename "'+ path +'" does not exist')
            path = ''
            s = ''
            curses.noecho()
            curses.curs_set(False)
            menu.refresh()
            time.sleep(2)
            continue
        elif not re.match('^[\w]+$', s):
            menu.addstr(2,1, 'error: filename must use only letters and numbers')
            path = ''
            s = ''
            curses.noecho()
            curses.curs_set(False)
            menu.refresh()
            time.sleep(2)
            continue
        menu.addstr(2,1, 'selecting file: ' + path)
        curses.noecho()
        curses.curs_set(False)
        menu.refresh()
        time.sleep(2)
        return path

# Giant main function for where the program starts
def main(stdscr):
    # Required to be global for buggy resize windows, requires reassignment of values
    global MAP_HEIGHT, MAP_WIDTH
    y = 1
    x = 1
    midy = int(MAP_HEIGHT / 2) # FIXME: mid points break on too small maps
    midx = int(MAP_WIDTH / 2)
    # Colours for different objects
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, 57, 234) # Wall
    curses.init_pair(2, 35, 0) # Player
    curses.init_pair(3, 60, 0) # Floor
    curses.curs_set(0)
    game_objects = {}
    while not game_objects:
        game_objects = menu()
    mapsize = game_objects['mapsize']
    # make a second window for getch and for displaying the map, this reduces flickering on getch refreshes
    stats_y = 2
    stats_x = MAP_WIDTH + 2
    stats = curses.newwin(5, 15, stats_y, MAP_WIDTH + 1)
    win = curses.newwin(WIN_HEIGHT, WIN_WIDTH, 0, 0)
    map = curses.newwin(MAP_HEIGHT, MAP_WIDTH, 0, 0)
    map.border(0)
    map.nodelay(True)
    win.nodelay(True) # Makes getch non blocking
    win.keypad(True)
    map.keypad(True)
    # Main ncurses loop, draw map, accept user input, shift map drawing
    while True:
        # Get keyboard input
        c = win.getch()
        curses.flushinp() # cleans extra getch characters
        if c == ord('a') or c == curses.KEY_LEFT: # Move left
            if game_objects[get_yx_key(y+midy,x+midx-1)].ch != WALLCH:
                x -= 1
        elif c == ord('d') or c == curses.KEY_RIGHT: # Move right
            if game_objects[get_yx_key(y+midy,x+midx+1)].ch != WALLCH:
                x += 1
        elif c == ord('s') or c == curses.KEY_DOWN: # Move down
            if game_objects[get_yx_key(y+midy+1,x+midx)].ch != WALLCH:
                y += 1
        elif c == ord('w') or c == curses.KEY_UP: # Move up
            if game_objects[get_yx_key(y+midy-1,x+midx)].ch != WALLCH:
                y -= 1
        elif False and c == ord("+"): # Buggy resize of screen (experimental feature, may break stuff)
            stats.clear()
            win.clear()
            map.clear()
            stdscr.clear()
            MAP_HEIGHT += 5
            MAP_WIDTH += 10
            stats.mvwin(stats_y, MAP_WIDTH + 2)
            stats.refresh()
            win.refresh()
            map.refresh()
            stdscr.refresh()
        elif False and c == ord("-"): # Buggy resize of screen (experimental feature, may break stuff)
            stats.clear()
            win.clear()
            map.clear()
            stdscr.clear()
            MAP_HEIGHT -= 5
            MAP_WIDTH -= 10
            stats.mvwin(stats_y, MAP_WIDTH + 2)
            stats.refresh()
            win.refresh()
            map.refresh()
            stdscr.refresh()
        elif c == ord('q') or c == ord('Q'):
            exit(0)
        # Draw stats window for position info, etc
        try:
            map.clear()
            stats.clear()
            stats.addstr(1,1,'pos_x:' + str(x))
            stats.addstr(2,1,'pos_y:' + str(y))
        except curses.error: # Passing ncurses errors allows for resizing of windows without crashing
            pass
        # Draw main map window, draw visible tiles, draw player
        for ty in range(y-1, y+MAP_HEIGHT):
            for tx in range(x-1, x+MAP_WIDTH):
                # Skip tiles that are outside map viewer
                if ty >= mapsize['y'] or ty < 0 or tx >= mapsize['x'] or tx < 0:
                    continue
                # key is the index for all tiles
                key = get_yx_key(ty,tx)
                # Get relative positions to left corner of screen (x,y)
                go_y = game_objects[key].y - y
                go_x = game_objects[key].x - x
                # Draw tiles
                try:
                    if (go_y > 0 and go_y < MAP_HEIGHT - 1) and (go_x > 0 and go_x < MAP_WIDTH - 1):
                        if game_objects[key].ch == WALLCH:
                            map.addstr(game_objects[key].y - y, game_objects[key].x - x, game_objects[key].ch, curses.color_pair(1))
                        else:
                            map.addstr(game_objects[key].y - y, game_objects[key].x - x, game_objects[key].ch, curses.color_pair(3))
                    if go_y == midy and go_x == midx:
                        map.addstr(go_y, go_x, 'P', curses.color_pair(2))
                except curses.error: # Passing ncurses errors allows for resizing of windows without crashing
                    pass
        # Window cleanup for screen update and resizing
        map.border(0)
        map.resize(MAP_HEIGHT, MAP_WIDTH)
        stats.resize(5,15)
        stats.border(0)
        # Fake refresh, prepares data structures but does not change screen
        stats.noutrefresh()
        map.noutrefresh()
        time.sleep(0.1)
        # Doupdate redraws the screen
        if c != curses.ERR or curses.KEY_RESIZE:
            curses.doupdate()

# Wrapper starts ncurses program, and fixes terminal glitches at end of program
if __name__ == '__main__':
    wrapper(main)
