import arcade
import math


class Projectile(arcade.Sprite):
    def __init__(self, x, y, dx, dy, damage, shooter, speed=10, scale=0.2):
        super().__init__("assets/arrow.png", scale)
        tip_offset = self.width * 0.95
        self.anchor_x = tip_offset
        self.anchor_y = self.height / 2

        self.center_x = x
        self.center_y = y

        length = math.hypot(dx, dy) or 1e-6
        dx_norm = dx / length
        dy_norm = dy / length

        self.change_x = dx_norm * speed
        self.change_y = dy_norm * speed

        self.angle = math.degrees(math.atan2(dy_norm, dx_norm))
        self.damage = damage
        self.shooter = shooter
        self.lifetime = 4.0

    def update(self, delta_time: float):
        self.center_x += self.change_x * delta_time * 60
        self.center_y += self.change_y * delta_time * 60

        self.lifetime -= delta_time
        if self.lifetime <= 0:
            self.kill()
            return
        