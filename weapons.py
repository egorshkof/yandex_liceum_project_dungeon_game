import time
import math
import arcade

from projectiles import Projectile


class Weapon:
    def __init__(self, owner, cooldown):
        self.owner = owner
        self.cooldown = cooldown
        self.last_attack_time = 0

    def can_attack(self):
        return time.time() - self.last_attack_time >= self.cooldown


class MeleeWeapon(Weapon):
    def __init__(self, owner, damage=20, range_x=50, range_y=35, cooldown=0.6):
        super().__init__(owner, cooldown)
        self.damage = damage
        self.range_x = range_x
        self.range_y = range_y

    def attack(self, targets):
        if not self.can_attack():
            return False

        direction = 1 if self.owner.change_x >= 0 else -1
        if direction == 0 and hasattr(self.owner, 'facing'):
            direction = self.owner.facing

        hitbox = arcade.SpriteSolidColor(self.range_x, self.range_y, arcade.color.TRANSPARENT_BLACK)
        hitbox.center_x = self.owner.center_x + direction * (self.range_x / 2 + 15)
        hitbox.center_y = self.owner.center_y

        hits = arcade.check_for_collision_with_list(hitbox, targets)
        for target in hits:
            if hasattr(target, 'take_damage'):
                target.take_damage(self.damage)

        self.last_attack_time = time.time()
        return True


class RangedWeapon(Weapon):
    def __init__(self, owner, damage=10, speed=10, cooldown=0.8):
        super().__init__(owner, cooldown)
        self.damage = damage
        self.speed = speed

    def attack(self, target_x, target_y, scene):
        if not self.can_attack():
            return False

        dx = target_x - self.owner.center_x
        dy = target_y - self.owner.center_y
        dist = max(1, math.hypot(dx, dy))
        proj = Projectile(
            self.owner.center_x,
            self.owner.center_y,
            dx / dist,
            dy / dist,
            self.damage,
            self.owner,
            self.speed
        )
        scene["Projectiles"].append(proj)
        self.last_attack_time = time.time()
        return True
