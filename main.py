import arcade
import arcade.gui
import time
import math

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "Dungeon Platformer"

TILE_SCALING = 1.0
PLAYER_SCALING = 0.4
ENEMY_SCALING = 0.4

GRAVITY = 1.2
PLAYER_MOVEMENT_SPEED = 5
PLAYER_JUMP_SPEED = 15

LAYER_OPTIONS = {
    "walls": {"use_spatial_hash": True},
    "ladders": {"use_spatial_hash": True},
}

# ---------------- PROJECTILE ---------------- #


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

    def update(self, delta_time):
        self.center_x += self.change_x * delta_time * 60
        self.center_y += self.change_y * delta_time * 60
        self.lifetime -= delta_time
        if self.lifetime <= 0:
            self.kill()


# ---------------- WEAPON ---------------- #

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


# ---------------- CHARACTERS ---------------- #

class Character(arcade.Sprite):
    def __init__(self, image, scale, max_hp):
        super().__init__(image, scale)
        self.max_hp = max_hp
        self.hp = max_hp
        self.facing = 1

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.kill()

    def is_alive(self):
        return self.hp > 0


class Player(Character):
    def __init__(self):
        super().__init__("assets/player.png", PLAYER_SCALING, max_hp=100)
        self.change_x = 0
        self.change_y = 0
        self.melee = MeleeWeapon(self, damage=25, cooldown=0.55)
        self.ranged = RangedWeapon(self, damage=12, cooldown=0.65)
        self.physics_engine = None

    def update(self, delta_time):
        if self.change_x > 0:
            self.facing = 1
        elif self.change_x < 0:
            self.facing = -1


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

    def update(self, player, delta_time):
        if not self.is_alive():
            return

        distance = arcade.get_distance_between_sprites(self, player)
        if distance <= self.aggro_range:
            direction = 1 if player.center_x > self.center_x else -1
            self.change_x = self.speed * direction
            self.facing = direction
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
        if self.aggro_range >= distance > 50:
            self.ranged.attack(player.center_x, player.center_y, scene)

        direction = 1 if player.center_x > self.center_x else -1
        self.change_x = self.speed * direction * 0.3
        self.facing = direction

        if self.physics_engine:
            self.physics_engine.update()


# ---------------- GAME VIEW ---------------- #

class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.scene = None
        self.player = None
        self.physics_engine = None
        self.camera = None
        self.gui_camera = None
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.enemies = arcade.SpriteList()
        self.hp_text = None

    def setup(self):
        tile_map = arcade.load_tilemap("assets/level_1.tmx", scaling=TILE_SCALING, layer_options=LAYER_OPTIONS)
        self.scene = arcade.Scene.from_tilemap(tile_map)

        if "Projectiles" not in self.scene:
            self.scene.add_sprite_list("Projectiles")

        self.player = Player()
        self.player.center_x = 128
        self.player.center_y = 256
        self.scene.add_sprite("Player", self.player)

        enemy1 = MeleeEnemy()
        enemy1.center_x = 600
        enemy1.center_y = 256

        enemy2 = ArcherEnemy()
        enemy2.center_x = 950
        enemy2.center_y = 300

        self.enemies.extend([enemy1, enemy2])
        self.scene.add_sprite_list("Enemies", sprite_list=self.enemies)

        ladders = self.scene["ladders"] if "ladders" in self.scene else None

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player,
            walls=self.scene["walls"],
            gravity_constant=GRAVITY,
            ladders=ladders
        )

        for enemy in self.enemies:
            enemy.physics_engine = arcade.PhysicsEnginePlatformer(
                enemy,
                walls=self.scene["walls"],
                gravity_constant=GRAVITY,
                ladders=ladders
            )

        self.camera = arcade.Camera2D()
        self.gui_camera = arcade.Camera2D()

        self.hp_text = arcade.Text(
            text=f"HP: {int(self.player.hp)}/{self.player.max_hp}",
            x=50,
            y=SCREEN_HEIGHT - 70,
            color=arcade.color.WHITE,
            font_size=15,
            width=300,
            align="left",
            anchor_x="left",
            anchor_y="top"
        )

    def center_camera(self):
        self.camera.position = self.player.position

    def on_update(self, delta_time):
        self.player.change_x = 0
        if self.left_pressed:
            self.player.change_x = -PLAYER_MOVEMENT_SPEED
        if self.right_pressed:
            self.player.change_x = PLAYER_MOVEMENT_SPEED

        if self.physics_engine.is_on_ladder():
            self.player.change_y = 0
            if self.up_pressed:
                self.player.change_y = PLAYER_MOVEMENT_SPEED
            elif self.down_pressed:
                self.player.change_y = -PLAYER_MOVEMENT_SPEED

        self.physics_engine.update()
        self.player.update(delta_time)

        for enemy in self.enemies:
            if isinstance(enemy, ArcherEnemy):
                enemy.update(self.player, delta_time, self.scene)
            else:
                enemy.update(self.player, delta_time)

        projectiles = self.scene["Projectiles"]
        for proj in list(projectiles):
            hit = False
            if proj.shooter is self.player:
                hits = arcade.check_for_collision_with_list(proj, self.enemies)
                for enemy in hits:
                    if enemy.is_alive():
                        enemy.take_damage(proj.damage)
                        hit = True
                        break
            elif isinstance(proj.shooter, Enemy):
                if arcade.check_for_collision(proj, self.player) and self.player.is_alive():
                    self.player.take_damage(proj.damage)
                    hit = True
            if hit:
                proj.kill()

        # Melee damage from enemies
        for enemy in self.enemies:
            if (isinstance(enemy, MeleeEnemy) and
                    enemy.is_alive() and
                    arcade.check_for_collision(self.player, enemy) and
                    enemy.melee.can_attack() and
                    self.player.is_alive()):
                self.player.take_damage(enemy.melee.damage)
                enemy.melee.last_attack_time = time.time()

        if not self.player.is_alive():
            self.setup()
            return

        self.hp_text.text = f"HP: {int(self.player.hp)}/{self.player.max_hp}"
        self.center_camera()
        projectiles.update(delta_time)

    def on_draw(self):
        self.clear()

        with self.camera.activate():
            self.scene.draw()
            self.scene["Projectiles"].draw()

        with self.gui_camera.activate():
            bar_width = 300
            bar_height = 25
            left = 50
            bottom = SCREEN_HEIGHT - 50

            arcade.draw_lbwh_rectangle_filled(left, bottom, bar_width, bar_height, arcade.color.DARK_RED)
            health_width = max(0, bar_width * (self.player.hp / self.player.max_hp))
            arcade.draw_lbwh_rectangle_filled(left, bottom, health_width, bar_height, arcade.color.RED)

            self.hp_text.draw()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.A:
            self.left_pressed = True
        elif key == arcade.key.D:
            self.right_pressed = True
        elif key == arcade.key.W:
            self.up_pressed = True
        elif key == arcade.key.S:
            self.down_pressed = True
        elif key == arcade.key.SPACE:
            if self.physics_engine.can_jump():
                self.player.change_y = PLAYER_JUMP_SPEED
        elif key == arcade.key.J:
            self.player.melee.attack(self.enemies)
        elif key == arcade.key.K:
            tx = self.player.center_x + 400 * self.player.facing
            ty = self.player.center_y
            self.player.ranged.attack(tx, ty, self.scene)

    def on_key_release(self, key, modifiers):
        if key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.D:
            self.right_pressed = False
        elif key == arcade.key.W:
            self.up_pressed = False
        elif key == arcade.key.S:
            self.down_pressed = False

# ---------------- MENU ---------------- #


class MenuView(arcade.View):
    def __init__(self):
        super().__init__()
        self.manager = arcade.gui.UIManager()

    def on_show_view(self):
        self.manager.enable()
        self.manager.clear()
        start_button = arcade.gui.UIFlatButton(text="Играть", width=200, height=50)

        @start_button.event("on_click")
        def on_click(event):
            game = GameView()
            game.setup()
            self.window.show_view(game)

        v_box = arcade.gui.UIBoxLayout()
        v_box.add(start_button)

        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(child=v_box, anchor_x="center_x", anchor_y="center_y")
        self.manager.add(anchor)

    def on_draw(self):
        self.clear()
        self.manager.draw()


def main():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    window.show_view(MenuView())
    arcade.run()


if __name__ == "__main__":
    main()
