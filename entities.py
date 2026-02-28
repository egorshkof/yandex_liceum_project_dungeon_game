import arcade
import random
import time

from weapons import MeleeWeapon, RangedWeapon
from utils import has_line_of_sight

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "Dungeon Platformer"

TILE_SCALING = 1.0
PLAYER_SCALING = 1.2
ENEMY_SCALING = 0.5

GRAVITY = 1.2
PLAYER_MOVEMENT_SPEED = 7
PLAYER_JUMP_SPEED = 15

LAYER_OPTIONS = {
    "walls": {"use_spatial_hash": True},
    "ladders": {"use_spatial_hash": True},
}


class Character(arcade.Sprite):
    def __init__(self, image, scale, max_hp):
        super().__init__(image, scale)
        self.max_hp = max_hp
        self.hp = max_hp
        self.facing = 1
        self.armor = 0.0

    def take_damage(self, amount):
        reduced = amount * (1 - self.armor)
        self.hp -= reduced

        if self.hp <= 0:
            self.kill()

    def is_alive(self):
        return self.hp > 0


"""
self.idle_textures = [arcade.load_texture(f"assets/knight/idle/idle_{i}.png") for i in range(1, 11)]
        self.walk_textures = [arcade.load_texture(f"assets/knight/run/run_{i}.png") for i in range(1, 11)]
        self.attack_textures = [arcade.load_texture(f"assets/knight/attack/attack_{i}.gif") for i in range(1, 11)]
"""


class Player(Character):
    def __init__(self):
        super().__init__(None, PLAYER_SCALING, max_hp=100)
        self.idle_textures = [arcade.load_texture(f"assets/knight/idle/idle_{i}.png") for i in range(1, 11)]
        self.walk_textures = [arcade.load_texture(f"assets/knight/run/run_{i}.png") for i in range(1, 11)]
        self.attack_textures = [arcade.load_texture(f"assets/knight/attack/attack_{i}.gif") for i in range(1, 11)]

        self.textures = self.idle_textures
        self.cur_texture_index = 0
        self.texture = self.textures[0]

        self.frame_time = 0.0
        self.frame_duration = 0.1

        self.melee = MeleeWeapon(self, damage=25, cooldown=0.55)
        self.ranged = RangedWeapon(self, damage=10, cooldown=0.0)

        self.base_scale = PLAYER_SCALING
        self.scale_x = self.base_scale
        self.scale_y = self.base_scale

        self.facing = 1
        self.regen_per_second = 0.5
        self.last_attack_time = 0.0

        # ===== Система заряда выстрела =====
        self.is_charging = False
        self.charge_time = 0.0
        self.max_charge_time = 2.0
        self.min_damage = 10
        self.max_damage = 40

    # ---------- Заряд ----------
    def start_charging(self):
        self.is_charging = True
        self.charge_time = 0.0

    def release_shot(self, target_x, target_y, scene):
        if not self.is_charging:
            return

        charge_ratio = min(1.0, self.charge_time / self.max_charge_time)
        damage = self.min_damage + (self.max_damage - self.min_damage) * charge_ratio

        # временно меняем урон
        original_damage = self.ranged.damage
        self.ranged.damage = damage
        self.ranged.attack(target_x, target_y, scene)
        self.ranged.damage = original_damage

        self.is_charging = False
        self.charge_time = 0.0

    # ---------- Update ----------
    def update(self, delta_time):

        if self.change_x > 0:
            self.facing = 1
        elif self.change_x < 0:
            self.facing = -1

        self.scale_x = self.base_scale * self.facing

        if self.hp < self.max_hp and self.is_alive():
            self.hp = min(self.max_hp, self.hp + self.regen_per_second * delta_time)

        if self.is_charging:
            self.charge_time += delta_time

        now = time.time()
        attack_duration = 0.5

        if now - self.last_attack_time < attack_duration:
            new_textures = self.attack_textures
        elif abs(self.change_x) > 0.1 or abs(self.change_y) > 0.1:
            new_textures = self.walk_textures
        else:
            new_textures = self.idle_textures

        if new_textures is not self.textures:
            self.textures = new_textures
            self.cur_texture_index = 0
            self.frame_time = 0.0

        self.frame_time += delta_time
        if self.frame_time >= self.frame_duration:
            self.frame_time -= self.frame_duration
            self.cur_texture_index = (
                self.cur_texture_index + 1
            ) % len(self.textures)
            self.texture = self.textures[self.cur_texture_index]

    def attack_melee(self, targets):
        self.melee.attack(targets)

    def attack_ranged(self, target_x, target_y, scene):
        self.ranged.attack(target_x, target_y, scene)


class Enemy(Character):
    def __init__(self, image, scale, max_hp, aggro_range=320):
        super().__init__(image, scale, max_hp)
        self.aggro_range = aggro_range
        self.change_x = 0
        self.change_y = 0
        self.physics_engine = None


class MeleeEnemy(Enemy):
    def __init__(self):
        super().__init__("assets/enemy_sword.png", ENEMY_SCALING, max_hp=60, aggro_range=220)
        self.melee = MeleeWeapon(self, damage=18, range_x=50, range_y=40, cooldown=1.0)
        self.speed = 2.2

    def update(self, player, delta_time, walls):
        if not self.is_alive():
            return

        distance = arcade.get_distance_between_sprites(self, player)

        if distance <= self.aggro_range:
            if has_line_of_sight(self, player, walls):
                direction = 1 if player.center_x > self.center_x else -1
                self.change_x = self.speed * direction
                self.facing = direction
            else:
                self.change_x = 0
        else:
            self.change_x = 0

        if self.physics_engine:
            self.physics_engine.update()


class ArcherEnemy(Enemy):
    def __init__(self):
        super().__init__("assets/enemy_bow.png", ENEMY_SCALING, max_hp=40, aggro_range=450)
        self.ranged = RangedWeapon(self, damage=9, speed=9, cooldown=1.3)
        self.speed = 0.5

    def update(self, player, delta_time, scene):
        if not self.is_alive():
            return

        distance = arcade.get_distance_between_sprites(self, player)

        walls = scene["walls"] if "walls" in scene else arcade.SpriteList()

        can_see = distance <= self.aggro_range and has_line_of_sight(self, player, walls)

        if can_see and distance > 50:
            self.ranged.attack(player.center_x, player.center_y, scene)

        if can_see:
            direction = 1 if player.center_x > self.center_x else -1
            self.change_x = self.speed * direction
            self.facing = direction
        else:
            self.change_x = 0

        if self.physics_engine:
            self.physics_engine.update()
