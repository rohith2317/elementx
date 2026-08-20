This folder is unused by default — every character, enemy, and UI
element in ELEMENTX is drawn procedurally with Pygame primitives
(rects, circles, polygons) so the game runs with zero external image
assets and zero copyright risk.

If you want to swap in your own sprite art, load images here with
pygame.image.load() and update game/player.py / game/enemy.py draw()
methods to blit your sprites instead of the procedural shapes.
