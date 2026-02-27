import arcade
import math


def has_line_of_sight(start_sprite, end_sprite, walls: arcade.SpriteList, step_size=6):
    if not walls:
        return True

    x1, y1 = start_sprite.center_x, start_sprite.center_y
    x2, y2 = end_sprite.center_x, end_sprite.center_y

    dx = x2 - x1
    dy = y2 - y1
    distance = math.hypot(dx, dy)

    if distance < 10:
        return True

    steps = max(2, int(distance / step_size) + 1)
    step_x = dx / steps
    step_y = dy / steps

    for i in range(1, steps):
        check_x = x1 + step_x * i
        check_y = y1 + step_y * i

        probe = arcade.SpriteSolidColor(8, 8, arcade.color.TRANSPARENT_BLACK)
        probe.center_x = check_x
        probe.center_y = check_y

        if arcade.check_for_collision_with_list(probe, walls):
            return False

    return True
