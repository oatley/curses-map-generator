# curses-map-generator
This map generator is quite slow and not optimized. Maps larger than 300 may take very long times to create. 
All maps are stored as compressed(gzip) json files. 
All maps are compatible between [maps-rust](https://github.com/oatley/maps-rust), which is a faster version with no loading bars.

# Warnings
- Linux Only. Python Curses may not be installed by default on windows.
- The "resources/maps" and "resources/html_maps" need to be created. The program will try and create them.

# How to use
To use the program:
```
python3 maps.py 
```

Controls:
```
move left   - a (or left arrow)
move right  - d (or right arrow)
move up     - w (or up arrow)
move down   - s (or down arrow)
exit map    - ctrl + c
```
