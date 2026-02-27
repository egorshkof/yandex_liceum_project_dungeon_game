import arcade


class Projectile(arcade.Sprite):
    def __init__(self, x, y, dx, dy, damage, shooter, speed=10, scale=0.5):
        super().__init__("assets/arrow.png", scale)
        self.center_x = x
        self.center_y = y
        self.change_x = dx * speed
        self.change_y = dy * speed
        self.damage = damage
        self.shooter = shooter
        self.lifetime = 4.0

    def update(self, delta_time: float, walls=None):
        # двигаемся
        self.center_x += self.change_x * delta_time * 60
        self.center_y += self.change_y * delta_time * 60

        self.lifetime -= delta_time
        if self.lifetime <= 0:
            self.kill()
            return

        # проверка столкновения со стенами
        if walls and arcade.check_for_collision_with_list(self, walls):
            self.kill()
            return